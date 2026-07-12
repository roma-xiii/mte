// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

mod commands;

use tauri::{Builder, Manager, WebviewUrl, WebviewWindowBuilder};

fn main() {
    Builder::default()
        .setup(|app| {
            let app_handle = app.handle();
            println!("App data dir: {:?}", app_handle.path().app_data_dir());
            let main_window = WebviewWindowBuilder::new(
                app,
                "home",
                WebviewUrl::App("html/home.html".into()),
            )
            .title("Mutations Trading Engine")
            .inner_size(300.0, 768.0)
            .build()?;

            main_window.set_focus()?;

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::windows_commands::apikeys_open,
            commands::windows_commands::chart_open,
            commands::windows_commands::positions_open,
            commands::backtest_commands::backtest_open,
        ])
        .run(tauri::generate_context!())
        .expect("Ошибка запуска приложения");
}
