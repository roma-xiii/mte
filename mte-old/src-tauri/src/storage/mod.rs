// src/db/mod.rs
use sqlx::{sqlite::SqlitePool, Row};
use anyhow::Result;
use serde::{Deserialize, Serialize};

pub struct Database {
  pool: SqlitePool,
}


#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct ApiKeyEntity {
	pub id: Option<i64>,
	pub source: String,
	pub name: String,
	pub key: String,
	pub secret: String,
	pub created_at: Option<String>,
}

impl Database {
  pub async fn new() -> Result<Self> {
    // В Tauri 2 используйте правильный путь к базе данных
    let database_url = "sqlite:app.db?mode=rwc";
    let pool = SqlitePool::connect(database_url).await?;
    
    // Создаем таблицу если не существует
    sqlx::query(
      r#"
      CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source TEXT NOT NULL,
        name TEXT NOT NULL,
        key TEXT NOT NULL,
        secret TEXT NOT NULL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      )
      "#
    )
    .execute(&pool)
    .await?;

    Ok(Self { pool })
  }

  pub async fn get_all_api_keys(&self) -> Result<Vec<ApiKeyEntity>> {
    let rows = sqlx::query(
      r#"
      SELECT id, source, name, key, secret, created_at
      FROM api_keys
      ORDER BY created_at DESC
      "#
    )
    .fetch_all(&self.pool)
    .await?;

    let keys = rows.iter().map(|row| ApiKeyEntity {
      id: row.get("id"),
      source: row.get("source"),
      name: row.get("name"),
      key: row.get("key"),
      secret: row.get("secret"),
      created_at: row.get("created_at"),
    }).collect();

    Ok(keys)
  }

  pub async fn create(&self) -> Result<i64> {
    let result = sqlx::query(
      r#"
      INSERT INTO api_keys (source, name, key, secret)
      VALUES (?, ?, ?, ?)
      "#
    )
    .bind("binance")
    .bind("my binance")
    .bind("svdvsdvdsvdsvsd")
    .bind("sdvsdvdsvdsvsdv")
    .execute(&self.pool)
    .await?;

    Ok(result.last_insert_rowid())
  }
}