// use crate::cases::apikey_cases;
// use serde::{Deserialize, Serialize};
use crate::storage::{Database, ApiKeyEntity};

#[tauri::command]
pub async fn apikey_list() -> Result<Vec<ApiKeyEntity>, String> {
	println!("LIST");
	let db = Database::new().await.map_err(|e| e.to_string())?;
	db.get_all_api_keys().await.map_err(|e| e.to_string())
}

#[tauri::command]
pub async fn apikey_create(
) -> Result<i64, String> {
	println!("CREATE");
	println!("LIST");
	let db = Database::new().await.map_err(|e| e.to_string())?;
	db.create().await.map_err(|e| e.to_string())
}
