## Prerequisites

- [docker](https://docs.docker.com/get-docker/)
- [k6](https://k6.io/docs/get-started/installation/)

## Generating tests

To generate tests from the `spec.yaml` OpenAPI specification in this folder,
change directory to this directory and run the following.

```shell
./build.sh -t
```

This will generate a test script in the `/openapi/tests/gen` directory. The file will be named `script.js`.
Do not edit this file.

## Running tests

Change directory to the `/openapi/tests/gen` directory and run the following. Note that you
will need to pass the cloudfront domain of the environment it should target.

```shell
CF_DOMAIN=<cloudfront-domain-to-test> k6 run script.js
```

To run the test for a single route, pass the route template as an envar.

```shell
TEST_ROUTE="/api/v1/{teamId}/{projectId}/{codebaseId}/sbom" k6 run script.js
```

## Generating client code

To generate a client from the `spec.yaml` OpenAPI specification in this folder,
change directory to this directory and run the following.

```shell
./build.sh -c
```

This will generate a typescript client in the `/openapi/client/gen` directory.
The client code generator has not been customized, and is included to illustrate
the potential use cases for the OpenAPI specification file. Check back for future
updates as it evolves.
