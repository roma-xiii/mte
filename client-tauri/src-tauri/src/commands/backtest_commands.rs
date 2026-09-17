use std::sync::Mutex;
use std::time::Duration;

use futures_util::{SinkExt, StreamExt};
use serde::Serialize;
use serde_json::{json, Value};
use tauri::{AppHandle, Emitter, Manager};
use tokio::sync::{mpsc, oneshot};
use tokio_tungstenite::{connect_async, tungstenite::Message};

const WS_URL: &str = "ws://127.0.0.1:8765/ws";
const IO_TIMEOUT: Duration = Duration::from_secs(5);

#[derive(Clone, Debug, Serialize)]
pub struct ConnectionState {
  status: &'static str,
  revision: u64,
  error: Option<String>,
}

#[derive(Clone, Serialize)]
pub struct ServerEvent {
  revision: u64,
  payload: String,
}

struct Command {
  payload: String,
  sent: oneshot::Sender<Result<(), String>>,
}

struct Transport {
  connection: ConnectionState,
  tx: Option<mpsc::Sender<Command>>,
}

pub struct BacktestBridge {
  transport: Mutex<Transport>,
  snapshot: Mutex<Option<ServerEvent>>,
}

impl BacktestBridge {
  pub fn new() -> Self {
    Self {
      transport: Mutex::new(Transport {
        connection: ConnectionState {
          status: "connecting",
          revision: 0,
          error: None,
        },
        tx: None,
      }),
      snapshot: Mutex::new(None),
    }
  }

  pub fn init(app_handle: AppHandle) {
    tauri::async_runtime::spawn(async move {
      let bridge = app_handle.state::<BacktestBridge>();
      bridge
        .run_ws_loop(
          WS_URL,
          Duration::from_secs(2),
          |state| {
            let _ = app_handle.emit("backtest:connection", state);
          },
          |event| {
            let _ = app_handle.emit("backtest:event", event);
          },
        )
        .await;
    });
  }

  fn connection(&self) -> Result<ConnectionState, String> {
    Ok(
      self
        .transport
        .lock()
        .map_err(|e| e.to_string())?
        .connection
        .clone(),
    )
  }

  fn transition(
    &self,
    status: &'static str,
    tx: Option<mpsc::Sender<Command>>,
    error: Option<String>,
  ) -> ConnectionState {
    let mut transport = self.transport.lock().expect("bridge state poisoned");
    transport.tx = tx;
    transport.connection.status = status;
    transport.connection.revision += 1;
    if status == "connected" {
      transport.connection.error = None;
    } else if error.is_some() {
      transport.connection.error = error;
    }
    transport.connection.clone()
  }

  async fn run_ws_loop(
    &self,
    url: &str,
    retry_delay: Duration,
    on_connection: impl Fn(ConnectionState),
    on_event: impl Fn(ServerEvent),
  ) {
    loop {
      on_connection(self.transition("connecting", None, None));
      *self.snapshot.lock().expect("snapshot poisoned") = None;
      let result = tokio::time::timeout(IO_TIMEOUT, connect_async(url)).await;
      let error = match result {
        Ok(Ok((ws, _))) => {
          let (tx, mut rx) = mpsc::channel::<Command>(64);
          let state = self.transition("connected", Some(tx), None);
          let revision = state.revision;
          on_connection(state);
          let (mut write, mut read) = ws.split();
          loop {
            tokio::select! {
                message = read.next() => {
                    match message {
                        Some(Ok(Message::Text(payload))) => {
                            let event = ServerEvent { revision, payload };
                            if let Ok(value) = serde_json::from_str::<Value>(&event.payload) {
                                if value.get("type").and_then(Value::as_str) == Some("snapshot") {
                                    *self.snapshot.lock().expect("snapshot poisoned") = Some(event.clone());
                                }
                            }
                            on_event(event);
                        }
                        Some(Ok(Message::Ping(payload))) => {
                            match tokio::time::timeout(IO_TIMEOUT, write.send(Message::Pong(payload))).await {
                                Ok(Ok(())) => {},
                                _ => break "Сервер не отвечает при отправке Pong".to_string(),
                            }
                        }
                        Some(Ok(Message::Close(_))) | None => break "Сервер закрыл соединение".to_string(),
                        Some(Err(e)) => break e.to_string(),
                        _ => {},
                    }
                }
                command = rx.recv() => {
                    let Some(command) = command else { break "Канал команд закрыт".to_string() };
                    if command.sent.is_closed() { continue; }
                    let result = match tokio::time::timeout(IO_TIMEOUT, write.send(Message::Text(command.payload))).await {
                        Ok(Ok(())) => Ok(()),
                        Ok(Err(e)) => Err(e.to_string()),
                        Err(_) => Err("Истекло время отправки команды; результат неизвестен".to_string()),
                    };
                    let error = result.as_ref().err().cloned();
                    let _ = command.sent.send(result);
                    if let Some(error) = error { break error; }
                }
            }
          }
          // rx is dropped here: commands never carry over to another connection.
        }
        Ok(Err(e)) => e.to_string(),
        Err(_) => "Истекло время подключения к Python".to_string(),
      };
      on_connection(self.transition("disconnected", None, Some(error)));
      tokio::time::sleep(retry_delay).await;
    }
  }

  async fn send_cmd(&self, json: &str) -> Result<(), String> {
    let (sent, received) = oneshot::channel();
    {
      let transport = self.transport.lock().map_err(|e| e.to_string())?;
      let tx = transport
        .tx
        .as_ref()
        .ok_or("Нет подключения к Python. Дождитесь восстановления соединения.")?;
      tx.try_send(Command {
        payload: json.to_string(),
        sent,
      })
      .map_err(|_| {
        "Не удалось отправить команду: соединение закрыто или очередь заполнена".to_string()
      })?;
    }
    received
      .await
      .map_err(|_| "Соединение прервано до отправки команды".to_string())?
  }
}

#[tauri::command]
pub fn backtest_get_connection(app: AppHandle) -> Result<ConnectionState, String> {
  app.state::<BacktestBridge>().connection()
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
pub async fn backtest_start(app: tauri::AppHandle, config: String) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  let config: Value = serde_json::from_str(&config).map_err(|e| e.to_string())?;
  let msg = json!({"cmd": "start", "config": config}).to_string();
  bridge.send_cmd(&msg).await
}

#[tauri::command]
pub async fn backtest_pause(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  bridge.send_cmd(r#"{"cmd":"pause"}"#).await
}

#[tauri::command]
pub async fn backtest_resume(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  bridge.send_cmd(r#"{"cmd":"resume"}"#).await
}

#[tauri::command]
pub async fn backtest_speed(app: tauri::AppHandle, value: f64) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  let msg = format!(r#"{{"cmd":"speed","value":{}}}"#, value);
  bridge.send_cmd(&msg).await
}

#[tauri::command]
pub async fn backtest_stop(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  bridge.send_cmd(r#"{"cmd":"stop"}"#).await
}

#[tauri::command]
pub async fn backtest_list_data(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  bridge.send_cmd(r#"{"cmd":"list_data"}"#).await
}

#[tauri::command]
pub async fn backtest_list_strategies(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  bridge.send_cmd(r#"{"cmd":"list_strategies"}"#).await
}

#[tauri::command]
pub async fn backtest_delete_data(app: tauri::AppHandle, filename: String) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  let msg = json!({"cmd": "delete_data", "filename": filename}).to_string();
  bridge.send_cmd(&msg).await
}

#[tauri::command]
pub fn backtest_get_snapshot(app: tauri::AppHandle) -> Result<Option<ServerEvent>, String> {
  let bridge = app.state::<BacktestBridge>();
  let guard = bridge.snapshot.lock().map_err(|e| e.to_string())?;
  Ok(guard.clone())
}

#[tauri::command]
pub fn backtest_clear_snapshot(app: tauri::AppHandle) -> Result<(), String> {
  let bridge = app.state::<BacktestBridge>();
  let mut guard = bridge.snapshot.lock().map_err(|e| e.to_string())?;
  *guard = None;
  Ok(())
}

#[cfg(test)]
mod tests {
  use super::*;
  use std::sync::Arc;
  use tokio::net::TcpListener;
  use tokio_tungstenite::accept_async;

  // Start an isolated Python server with: python websocket_server.py --port 18765
  // Never point this test at a user's active session.
  #[tokio::test]
  #[ignore = "requires an isolated Nautilus server on 127.0.0.1:18765"]
  async fn nautilus_csv_smoke() {
    let bridge = Arc::new(BacktestBridge::new());
    let runner = bridge.clone();
    let (states_tx, mut states_rx) = mpsc::unbounded_channel();
    let (events_tx, mut events_rx) = mpsc::unbounded_channel();
    let task = tokio::spawn(async move {
      runner
        .run_ws_loop(
          "ws://127.0.0.1:18765/ws",
          Duration::from_millis(100),
          |state| {
            let _ = states_tx.send(state);
          },
          |event| {
            let _ = events_tx.send(event);
          },
        )
        .await;
    });
    wait_for_state(&mut states_rx, "connected").await;
    bridge
      .send_cmd(r#"{"cmd":"list_strategies"}"#)
      .await
      .unwrap();
    bridge.send_cmd(r#"{"cmd":"list_data"}"#).await.unwrap();
    let mut strategies = false;
    let mut data = false;
    while !strategies || !data {
      let event = tokio::time::timeout(Duration::from_secs(5), events_rx.recv())
        .await
        .unwrap()
        .unwrap();
      let value: Value = serde_json::from_str(&event.payload).unwrap();
      match value["type"].as_str() {
        Some("strategies_list") => {
          strategies = value["data"]
            .as_array()
            .unwrap()
            .iter()
            .any(|s| s["name"] == "sma_crossover")
        }
        Some("data_list") => {
          data = value["data"]
            .as_array()
            .unwrap()
            .iter()
            .any(|d| d["file"] == "BTCUSDT-1d.csv")
        }
        _ => {}
      }
    }
    bridge
      .send_cmd(
        &json!({"cmd": "start", "config": {
            "csv_file": "BTCUSDT-1d.csv", "timeframe": "1d", "speed": 100,
            "strategy_params": {"trade_size": 1}
        }})
        .to_string(),
      )
      .await
      .unwrap();
    let mut expected_bars = None;
    let mut bars = 0;
    tokio::time::timeout(Duration::from_secs(30), async {
      loop {
        let event = events_rx.recv().await.unwrap();
        let value: Value = serde_json::from_str(&event.payload).unwrap();
        match value["type"].as_str() {
          Some("ready") => expected_bars = value["total_bars"].as_u64(),
          Some("bar") => bars += 1,
          Some("error") => panic!("Nautilus error: {value}"),
          Some("complete") => break,
          _ => {}
        }
      }
    })
    .await
    .expect("backtest timeout");
    assert!(bars > 0);
    assert_eq!(Some(bars), expected_bars);
    println!("Nautilus smoke: catalogs loaded, ready received, {bars} bars, complete received");
    task.abort();
    let _ = task.await;
  }

  async fn wait_for_state(
    rx: &mut mpsc::UnboundedReceiver<ConnectionState>,
    status: &str,
  ) -> ConnectionState {
    tokio::time::timeout(Duration::from_secs(5), async {
      loop {
        let state = rx.recv().await.expect("state channel closed");
        if state.status == status {
          return state;
        }
      }
    })
    .await
    .expect("state timeout")
  }

  #[tokio::test]
  async fn disconnected_command_is_rejected_and_dropped_queue_is_not_success() {
    let bridge = Arc::new(BacktestBridge::new());
    assert!(bridge.send_cmd("start").await.is_err());
    let (tx, mut rx) = mpsc::channel(4);
    bridge.transition("connected", Some(tx), None);
    let request_bridge = bridge.clone();
    let request = tokio::spawn(async move { request_bridge.send_cmd("start").await });
    let queued = rx.recv().await.unwrap();
    assert!(!request.is_finished(), "success must wait for socket write");
    drop(queued);
    assert!(request.await.unwrap().is_err());
    bridge.transition("disconnected", None, Some("closed".into()));
    assert!(bridge.send_cmd("start").await.is_err());
  }

  #[tokio::test]
  async fn late_server_disconnect_and_reconnect_do_not_replay_commands() {
    let listener = TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();
    drop(listener);
    let bridge = Arc::new(BacktestBridge::new());
    let runner = bridge.clone();
    let (states_tx, mut states_rx) = mpsc::unbounded_channel();
    let (events_tx, mut events_rx) = mpsc::unbounded_channel();
    let task = tokio::spawn(async move {
      runner
        .run_ws_loop(
          &format!("ws://{addr}/ws"),
          Duration::from_millis(100),
          |state| {
            let _ = states_tx.send(state);
          },
          |event| {
            let _ = events_tx.send(event);
          },
        )
        .await;
    });
    wait_for_state(&mut states_rx, "disconnected").await;
    assert!(bridge.send_cmd("must-not-replay-1").await.is_err());

    let listener = TcpListener::bind(addr).await.unwrap();
    let (tcp, _) = tokio::time::timeout(Duration::from_secs(5), listener.accept())
      .await
      .unwrap()
      .unwrap();
    let mut server = accept_async(tcp).await.unwrap();
    let connected = wait_for_state(&mut states_rx, "connected").await;
    bridge.send_cmd(r#"{"cmd":"list_data"}"#).await.unwrap();
    assert_eq!(
      server.next().await.unwrap().unwrap().to_text().unwrap(),
      r#"{"cmd":"list_data"}"#
    );
    server
      .send(Message::Text(r#"{"type":"data_list","data":[]}"#.into()))
      .await
      .unwrap();
    let event = tokio::time::timeout(Duration::from_secs(2), events_rx.recv())
      .await
      .unwrap()
      .unwrap();
    assert_eq!(event.revision, connected.revision);
    assert!(event.payload.contains("data_list"));
    server.close(None).await.unwrap();
    drop(server);
    let disconnected = wait_for_state(&mut states_rx, "disconnected").await;
    assert!(disconnected.revision > connected.revision);
    assert!(bridge.send_cmd("must-not-replay-2").await.is_err());

    let (tcp, _) = tokio::time::timeout(Duration::from_secs(5), listener.accept())
      .await
      .unwrap()
      .unwrap();
    let mut server = accept_async(tcp).await.unwrap();
    let reconnected = wait_for_state(&mut states_rx, "connected").await;
    assert!(reconnected.revision > disconnected.revision);
    assert!(
      tokio::time::timeout(Duration::from_millis(100), server.next())
        .await
        .is_err()
    );
    bridge.send_cmd("new-command").await.unwrap();
    assert_eq!(
      server.next().await.unwrap().unwrap().to_text().unwrap(),
      "new-command"
    );
    task.abort();
    let _ = task.await;
  }
}
