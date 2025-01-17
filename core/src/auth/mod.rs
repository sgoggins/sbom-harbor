mod authenticator;

pub use authenticator::*;
use std::fmt::{Display, Formatter};

/// Enumerates the kinds of resources for which policies can be defined.
pub enum ResourceKind {
    /// Indicates that policy that can be applied to any resource.
    Any,
    /// Specifies that a policy applies to a [Team].
    Team,
    /// Specifies that a policy applies to a [Project].
    Project,
    /// Specifies that a policy applies to a [Codebase].
    Codebase,
    /// Specifies that a policy applies to a [Token].
    Token,
    /// Specifies that a policy applies to a [Group].
    Group,
}

impl Display for ResourceKind {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            ResourceKind::Any => write!(f, "*"),
            ResourceKind::Team => write!(f, "team"),
            ResourceKind::Project => write!(f, "project"),
            ResourceKind::Codebase => write!(f, "codebase"),
            ResourceKind::Token => write!(f, "token"),
            ResourceKind::Group => write!(f, "group"),
        }
    }
}
