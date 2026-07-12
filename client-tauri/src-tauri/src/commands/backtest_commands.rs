use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use tauri::Manager;

const WS_PORT: u16 = 8765;

pub struct BacktestProcess {
    child: Mutex<Option<Child>>,
}

impl BacktestProcess {
    pub fn new() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }
}

#[tauri::command]
pub fn backtest_open(app: tauri::AppHandle) {
    let label = "backtest";

    if let Some(existing_window) = app.get_webview_window(label) {
        existing_window.set_focus().expect("Не удалось установить фокус на окно");
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
    state: tauri::State<'_, BacktestProcess>,
) -> Result<String, String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;

    if child_guard.is_some() {
        return Err("Backtest server already running".to_string());
    }

    let python_script = find_ws_server()?;
    let python_bin = find_python()?;

    let child = Command::new(&python_bin)
        .arg(&python_script)
        .arg("--port")
        .arg(WS_PORT.to_string())
        .stderr(Stdio::inherit())
        .spawn()
        .map_err(|e| format!("Failed to spawn Python WS server: {}", e))?;

    *child_guard = Some(child);

    Ok(format!("ws://127.0.0.1:{}/ws", WS_PORT))
}

#[tauri::command]
pub fn backtest_stop(
    state: tauri::State<'_, BacktestProcess>,
) -> Result<(), String> {
    let mut child_guard = state.child.lock().map_err(|e| e.to_string())?;
    if let Some(ref mut child) = *child_guard {
        child.kill().ok();
        child.wait().ok();
    }
    *child_guard = None;
    Ok(())
}

pub fn cleanup_backtest(state: &BacktestProcess) {
    if let Ok(mut child_guard) = state.child.lock() {
        if let Some(ref mut child) = *child_guard {
            child.kill().ok();
            child.wait().ok();
        }
        *child_guard = None;
    }
}

fn find_python() -> Result<String, String> {
    for name in &["python3", "python"] {
        if Command::new(name).arg("--version").output().is_ok() {
            return Ok(name.to_string());
        }
    }
    Err("Python not found".to_string())
}

fn find_ws_server() -> Result<String, String> {
    for path in &[
        "../nautilus/websocket_server.py",
        "nautilus/websocket_server.py",
    ] {
        if std::path::Path::new(path).exists() {
            return Ok(path.to_string());
        }
    }
    Err("websocket_server.py not found".to_string())
}
