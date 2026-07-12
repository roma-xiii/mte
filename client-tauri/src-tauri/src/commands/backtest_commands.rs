use tauri::Manager;

pub struct BacktestServer;

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
