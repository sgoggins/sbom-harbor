use serde::{Deserialize, Serialize};
/*
 * Generated by: https://openapi-generator.tech
 */

/// Swid : Specifies metadata and content for ISO-IEC 19770-2 Software Identification (SWID) Tags.
#[derive(Clone, Debug, PartialEq, Default, Serialize, Deserialize)]
pub struct Swid {
    /// Maps to the tagId of a SoftwareIdentity.
    #[serde(rename = "tagId")]
    pub tag_id: String,
    /// Maps to the name of a SoftwareIdentity.
    #[serde(rename = "name")]
    pub name: String,
    /// Maps to the version of a SoftwareIdentity.
    #[serde(rename = "version", skip_serializing_if = "Option::is_none")]
    pub version: Option<String>,
    /// Maps to the tagVersion of a SoftwareIdentity.
    #[serde(rename = "tagVersion", skip_serializing_if = "Option::is_none")]
    pub tag_version: Option<i32>,
    /// Maps to the patch of a SoftwareIdentity.
    #[serde(rename = "patch", skip_serializing_if = "Option::is_none")]
    pub patch: Option<bool>,
    #[serde(rename = "text", skip_serializing_if = "Option::is_none")]
    pub text: Option<Box<crate::entities::cyclonedx::models::Attachment>>,
    /// The URL to the SWID file.
    #[serde(rename = "url", skip_serializing_if = "Option::is_none")]
    pub url: Option<String>,
}

impl Swid {
    /// Specifies metadata and content for ISO-IEC 19770-2 Software Identification (SWID) Tags.
    pub fn new(tag_id: String, name: String) -> Swid {
        Swid {
            tag_id,
            name,
            version: None,
            tag_version: None,
            patch: None,
            text: None,
            url: None,
        }
    }
}
