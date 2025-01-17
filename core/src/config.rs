use crate::Error;
use platform::config::from_env;
use platform::encoding::url_encode;
use platform::mongodb::Context;
use serde::{Deserialize, Serialize};

/// Returns the Snyk API token from an environment variable.
pub fn snyk_token() -> Result<String, Error> {
    match from_env("SNYK_TOKEN") {
        None => Err(Error::Config("Snyk token not set".to_string())),
        Some(v) => Ok(v),
    }
}

/// Returns the Harbor S3 bucket name.
pub fn harbor_bucket() -> Result<String, Error> {
    match from_env("HARBOR_FILE_STORE") {
        None => Err(Error::Config("Harbor bucket not set".to_string())),
        Some(v) => Ok(v),
    }
}

/// Returns a Mongo Context for used with the local devenv. Used by tests or for local development.
pub fn dev_context(db_name: Option<&str>) -> Result<Context, Error> {
    let db_name = match db_name {
        None => "harbor",
        Some(db_name) => db_name,
    };

    Ok(Context {
        host: "mongo".to_string(),
        username: "root".to_string(),
        password: "harbor".to_string(),
        port: 27017,
        db_name: db_name.to_string(),
        key_name: "id".to_string(),
        connection_uri: None,
    })
}

/// Returns a Context specific to the Harbor teams deployment environment.
pub fn harbor_context() -> Result<Context, Error> {
    let raw_config = match from_env("DOCDB_CONFIG") {
        None => {
            return Err(Error::Config("DocumentDB config not set".to_string()));
        }
        Some(raw_config) => raw_config,
    };

    let cfg: DocDbConfig = serde_json::from_str(raw_config.as_str())
        .map_err(|e| Error::Serde(format!("invalid DocumentDB config::{}", e)))?;

    Ok(cfg.to_context())
}

#[derive(Clone, Debug, Deserialize, Serialize)]
struct DocDbConfig {
    username: String,
    password: String,
    engine: String,
    port: u32,
    host: String,
    ssl: bool,
    #[serde(rename = "dbInstanceIdentifier")]
    db_instance_identifier: String,
}

impl DocDbConfig {
    fn to_context(&self) -> Context {
        let connection_uri = format!(
            "mongodb://{}:{}@{}:{}/?ssl={}&tlsCAFile=rds-combined-ca-bundle.pem&retryWrites=false",
            url_encode(self.username.as_str()),
            url_encode(self.password.as_str()),
            //self.db_instance_identifier,
            self.host,
            self.port,
            self.ssl
        );

        Context {
            host: "".to_string(),
            username: "".to_string(),
            password: "".to_string(),
            port: 0,
            db_name: "harbor".to_string(),
            key_name: "id".to_string(),
            connection_uri: Some(connection_uri),
        }
    }
}
