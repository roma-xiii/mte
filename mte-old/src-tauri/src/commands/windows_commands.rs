use tauri::{WebviewUrl, WebviewWindowBuilder};

#[tauri::command]
pub fn apikeys_open(app: tauri::AppHandle) {
	let label = format!("apikeys");

	WebviewWindowBuilder::new(
		&app,
		&label,
		WebviewUrl::App("html/api-keys.html".into())
	)
	.title("MTE - ApiKeys")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}

#[tauri::command]
pub fn watchlist_open(app: tauri::AppHandle) {
	let label = format!("watchlist");

	WebviewWindowBuilder::new(
		&app,
		&label,
		WebviewUrl::App("html/watchlist.html".into())
	)
	.title("MTE - Watchlist")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}

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

#[tauri::command]
pub fn portfolios_open(app: tauri::AppHandle) {
	let label = format!("portfolios");

	WebviewWindowBuilder::new(
		&app,
		&label,
		WebviewUrl::App("html/portfolios.html".into())
	)
	.title("MTE - Portfolios")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}

#[tauri::command]
pub fn trading_open(app: tauri::AppHandle) {
	let label = format!("trading");

	WebviewWindowBuilder::new(
		&app,
		&label,
		WebviewUrl::App("html/trading.html".into())
	)
	.title("MTE - Trading")
	.inner_size(800.0, 600.0)
	.build()
	.expect("Не удалось создать окно");
}
