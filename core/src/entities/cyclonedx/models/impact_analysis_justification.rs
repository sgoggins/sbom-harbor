use serde::{Deserialize, Serialize};
/*
 * Generated by: https://openapi-generator.tech
 */

/// The rationale of why the impact analysis state was asserted.   * __code\\_not\\_present__ = the code has been removed or tree-shaked.  * __code\\_not\\_reachable__ = the vulnerable code is not invoked at runtime.  * __requires\\_configuration__ = exploitability requires a configurable option to be set/unset.  * __requires\\_dependency__ = exploitability requires a dependency that is not present.  * __requires\\_environment__ = exploitability requires a certain environment which is not present.  * __protected\\_by\\_compiler__ = exploitability requires a compiler flag to be set/unset.  * __protected\\_at\\_runtime__ = exploits are prevented at runtime.  * __protected\\_at\\_perimeter__ = attacks are blocked at physical, logical, or network perimeter.  * __protected\\_by\\_mitigating\\_control__ = preventative measures have been implemented that reduce the likelihood and/or impact of the vulnerability.
#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd, Hash, Serialize, Deserialize)]
pub enum ImpactAnalysisJustification {
    #[serde(rename = "code_not_present")]
    CodeNotPresent,
    #[serde(rename = "code_not_reachable")]
    CodeNotReachable,
    #[serde(rename = "requires_configuration")]
    RequiresConfiguration,
    #[serde(rename = "requires_dependency")]
    RequiresDependency,
    #[serde(rename = "requires_environment")]
    RequiresEnvironment,
    #[serde(rename = "protected_by_compiler")]
    ProtectedByCompiler,
    #[serde(rename = "protected_at_runtime")]
    ProtectedAtRuntime,
    #[serde(rename = "protected_at_perimeter")]
    ProtectedAtPerimeter,
    #[serde(rename = "protected_by_mitigating_control")]
    ProtectedByMitigatingControl,
}

impl ToString for ImpactAnalysisJustification {
    fn to_string(&self) -> String {
        match self {
            Self::CodeNotPresent => String::from("code_not_present"),
            Self::CodeNotReachable => String::from("code_not_reachable"),
            Self::RequiresConfiguration => String::from("requires_configuration"),
            Self::RequiresDependency => String::from("requires_dependency"),
            Self::RequiresEnvironment => String::from("requires_environment"),
            Self::ProtectedByCompiler => String::from("protected_by_compiler"),
            Self::ProtectedAtRuntime => String::from("protected_at_runtime"),
            Self::ProtectedAtPerimeter => String::from("protected_at_perimeter"),
            Self::ProtectedByMitigatingControl => String::from("protected_by_mitigating_control"),
        }
    }
}

impl Default for ImpactAnalysisJustification {
    fn default() -> ImpactAnalysisJustification {
        Self::CodeNotPresent
    }
}
