use serde::{Deserialize, Serialize};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ApiKeyEntity {
	pub id: Option<i64>,
	pub source: String,
	pub name: String,
	pub key: String,
	pub secret: String,
	pub created_at: Option<String>,
}
