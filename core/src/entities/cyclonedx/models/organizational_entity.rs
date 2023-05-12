use serde::{Deserialize, Serialize};
/*
 * Generated by: https://openapi-generator.tech
 */

#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct OrganizationalEntity {
    /// The name of the organization
    #[serde(rename = "name", skip_serializing_if = "Option::is_none")]
    pub name: Option<String>,
    /// The URL of the organization. Multiple URLs are allowed.
    #[serde(rename = "url", skip_serializing_if = "Option::is_none")]
    pub url: Option<Vec<String>>,
    /// A contact at the organization. Multiple contacts are allowed.
    #[serde(rename = "contact", skip_serializing_if = "Option::is_none")]
    pub contact: Option<Vec<crate::entities::cyclonedx::models::OrganizationalContact>>,
}

impl OrganizationalEntity {
    pub fn new() -> OrganizationalEntity {
        OrganizationalEntity {
            name: None,
            url: None,
            contact: None,
        }
    }
}
