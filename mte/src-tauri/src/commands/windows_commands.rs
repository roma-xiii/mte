use tauri::{WebviewUrl, WebviewWindowBuilder, Manager};

#[tauri::command]
pub fn apikeys_open(app: tauri::AppHandle) {
	let label = "apikeys";

	// Проверяем, существует ли уже окно с данным лейблом
	if let Some(existing_window) = app.get_webview_window(label) {
		// Если окно существует, устанавливаем на него фокус
		existing_window.set_focus().expect("Не удалось установить фокус на окно");
		return;
	}

	// Если окна не существует, создаем новое
	WebviewWindowBuilder::new(
		&app,
		label,
		WebviewUrl::App("html/api-keys.html".into())
	)
	.title("MTE - ApiKeys")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}

// #[tauri::command]
// pub fn watchlist_open(app: tauri::AppHandle) {
// 	let label = format!("watchlist");

// 	WebviewWindowBuilder::new(
// 		&app,
// 		&label,
// 		WebviewUrl::App("html/watchlist.html".into())
// 	)
// 	.title("MTE - Watchlist")
// 	.inner_size(800.0, 600.0)
// 	.build()
// 	.expect("Не удалось создать окно");
// }

#[tauri::command]
pub fn chart_open(app: tauri::AppHandle) {
	let timestamp = std::time::SystemTime::now()
		.duration_since(std::time::UNIX_EPOCH)
		.expect("Time went backwards")
		.as_millis();

	let label = format!("chart-{}", timestamp);

	WebviewWindowBuilder::new(
		&app,
		&label,
		WebviewUrl::App("html/chart.html".into())
	)
	.title("MTE - Chart")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}

// #[tauri::command]
// pub fn portfolios_open(app: tauri::AppHandle) {
// 	let label = format!("portfolios");

// 	WebviewWindowBuilder::new(
// 		&app,
// 		&label,
// 		WebviewUrl::App("html/portfolios.html".into())
// 	)
// 	.title("MTE - Portfolios")
// 	.inner_size(800.0, 600.0)
// 	.build()
// 	.expect("Не удалось создать окно");
// }

#[tauri::command]
pub fn positions_open(app: tauri::AppHandle) {
	let label = "positions";

	// Проверяем, существует ли уже окно с данным лейблом
	if let Some(existing_window) = app.get_webview_window(label) {
		// Если окно существует, устанавливаем на него фокус
		existing_window.set_focus().expect("Не удалось установить фокус на окно");
		return;
	}

	// Если окна не существует, создаем новое
	WebviewWindowBuilder::new(
		&app,
		label,
		WebviewUrl::App("html/positions.html".into())
	)
	.title("MTE - Positions")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}
