#![feature(async_fn_in_trait)]
#![feature(error_iter)]
#![allow(incomplete_features)]
#![warn(missing_docs)]

//! The Platform crate encapsulates all functionality related to underlying platform services (e.g. databases,
//! AWS Managed services). It also includes a generic authorization module based on AWS IAM.

extern crate core;

/// The `auth` module provides a reusable RBAC model inspired by the AWS IAM model. It was initially
/// developed to solve multi-tenant database access, but as a general purpose RBAC model, it should be
/// usable in a variety of scenarios.
pub mod auth;

/// The `encoding` package provides exports and utility methods related to data encoding.
pub mod encoding;

/// The `cognito` module provides high level abstractions over the AWS Cognito SDK.
pub mod cognito;

/// The config module contains functions that are used to retrieve runtime configuration.
pub mod config;

/// The cryptography module contains convenience functions for common cryptographic operations.
pub mod cryptography;

/// The `errors` module provides common error types for the library.
pub mod errors;

/// The `hyper` module provides a lightweight HTTP client facade based on the `hyper` SDK.
pub mod hyper;

/// The `mongodb` module provides a `Service` and `Store` abstraction over common CRUD based operations
/// against a MongoDB or DocumentDB back end.
pub mod mongodb;

/// Implementation of the `thiserror` enum.
pub use errors::Error;

/// S3 Provider module
pub mod persistence;

/// Extensions to `std::time`.
pub mod time;
