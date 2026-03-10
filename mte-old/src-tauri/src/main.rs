mod commands;
mod cases;
mod storage;

use tauri::{WebviewUrl, Builder, WebviewWindowBuilder, Manager};

fn main() {
  Builder::default()
    .setup(|app| {
      let app_handle = app.handle();
      println!("App data dir: {:?}", app_handle.path().app_data_dir());
			let main_window = WebviewWindowBuilder::new(
        app,
        "home",
        WebviewUrl::App("html/home.html".into())
      )
      .title("Mutations Trading Engine")
      .inner_size(300.0, 768.0)
      .build()?;
      
      main_window.set_focus()?;
      
      Ok(())
    })
    .invoke_handler(tauri::generate_handler![
      commands::windows_commands::apikeys_open,
      commands::windows_commands::watchlist_open,
      commands::windows_commands::chart_open,
      commands::windows_commands::portfolios_open,
      commands::windows_commands::trading_open,
			commands::apikey_commands::apikey_list,
			commands::apikey_commands::apikey_create,
    ])
    .run(tauri::generate_context!())
    .expect("Ошибка запуска приложения");
}
