use std::sync::Mutex;
use std::time::Duration;

use futures_util::{SinkExt, StreamExt};
use serde_json::Value;
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::mpsc;
use tokio_tungstenite::connect_async;

const WS_URL: &str = "ws://127.0.0.1:8765";

pub struct BacktestBridge {
    ws_tx: Mutex<Option<mpsc::UnboundedSender<String>>>,
    snapshot: Mutex<Option<String>>,
}

impl BacktestBridge {
    pub fn new() -> Self {
        Self {
            ws_tx: Mutex::new(None),
            snapshot: Mutex::new(None),
        }
    }

    pub fn init(app_handle: AppHandle) {
        tauri::async_runtime::spawn(async move {
            Self::run_ws_loop(app_handle).await;
        });
    }

    async fn run_ws_loop(app_handle: AppHandle) {
        loop {
            let (tx, mut rx) = mpsc::unbounded_channel::<String>();

            if let Some(bridge) = app_handle.try_state::<BacktestBridge>() {
                if let Ok(mut guard) = bridge.ws_tx.lock() {
                    *guard = Some(tx);
                }
            }

            match connect_async(WS_URL).await {
                Ok((ws_stream, _)) => {
                    let (mut write, mut read) = ws_stream.split();

                    let incoming = async {
                        while let Some(Ok(msg)) = read.next().await {
                            if let Ok(text) = msg.to_text() {
                                let payload = text.to_string();

                                if let Ok(val) = serde_json::from_str::<Value>(&payload) {
                                    if val.get("type").and_then(|v| v.as_str()) == Some("snapshot")
                                    {
                                        if let Some(bridge) =
                                            app_handle.try_state::<BacktestBridge>()
                                        {
                                            if let Ok(mut guard) = bridge.snapshot.lock() {
                                                *guard = Some(payload.clone());
                                            }
                                        }
                                    }
                                }

                                let _ = app_handle.emit("backtest:event", &payload);
                            }
                        }
                    };

                    let outgoing = async {
                        while let Some(msg) = rx.recv().await {
                            if write
                                .send(tokio_tungstenite::tungstenite::Message::Text(msg))
                                .await
                                .is_err()
                            {
                                break;
                            }
                        }
                    };

                    tokio::select! {
                        _ = incoming => {},
                        _ = outgoing => {},
                    }
                }
                Err(e) => {
                    eprintln!("[backtest] WS connect failed: {e}. Retrying in 5s...");
                    tokio::time::sleep(Duration::from_secs(5)).await;
                }
            }
        }
    }

    fn send_cmd(&self, json: &str) -> Result<(), String> {
        let guard = self.ws_tx.lock().map_err(|e| e.to_string())?;
        let tx = guard
            .as_ref()
            .ok_or_else(|| "WebSocket not connected".to_string())?;
        tx.send(json.to_string()).map_err(|e| e.to_string())
    }
}

#[tauri::command]
pub fn backtest_open(app: tauri::AppHandle) {
    let label = "backtest";

    if let Some(existing_window) = app.get_webview_window(label) {
        existing_window
            .set_focus()
            .expect("Не удалось установить фокус на окно");
        return;
    }

    tauri::WebviewWindowBuilder::new(
        &app,
        label,
        tauri::WebviewUrl::App("html/backtest.html".into()),
    )
    .title("MTE - Backtest")
    .inner_size(1200.0, 800.0)
    .build()
    .expect("Не удалось создать окно");
}

#[tauri::command]
pub fn backtest_start(
    app: tauri::AppHandle,
    config: String,
) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    let msg = format!(r#"{{"cmd":"start","config":{}}}"#, config);
    bridge.send_cmd(&msg)
}

#[tauri::command]
pub fn backtest_pause(app: tauri::AppHandle) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    bridge.send_cmd(r#"{"cmd":"pause"}"#)
}

#[tauri::command]
pub fn backtest_resume(app: tauri::AppHandle) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    bridge.send_cmd(r#"{"cmd":"resume"}"#)
}

#[tauri::command]
pub fn backtest_speed(app: tauri::AppHandle, value: f64) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    let msg = format!(r#"{{"cmd":"speed","value":{}}}"#, value);
    bridge.send_cmd(&msg)
}

#[tauri::command]
pub fn backtest_stop(app: tauri::AppHandle) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    bridge.send_cmd(r#"{"cmd":"stop"}"#)
}

#[tauri::command]
pub async fn backtest_list_data(app: tauri::AppHandle) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    bridge.send_cmd(r#"{"cmd":"list_data"}"#)
}

#[tauri::command]
pub async fn backtest_list_strategies(app: tauri::AppHandle) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    bridge.send_cmd(r#"{"cmd":"list_strategies"}"#)
}

#[tauri::command]
pub async fn backtest_delete_data(app: tauri::AppHandle, filename: String) -> Result<(), String> {
    let bridge = app.state::<BacktestBridge>();
    let msg = format!(r#"{{"cmd":"delete_data","filename":"{}"}}"#, filename);
    bridge.send_cmd(&msg)
}

#[tauri::command]
pub fn backtest_get_snapshot(app: tauri::AppHandle) -> Result<Option<String>, String> {
    let bridge = app.state::<BacktestBridge>();
    let guard = bridge.snapshot.lock().map_err(|e| e.to_string())?;
    Ok(guard.clone())
}
