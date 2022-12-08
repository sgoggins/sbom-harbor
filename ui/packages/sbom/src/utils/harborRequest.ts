/**
 * Factory to create a function that will make a request to the Harbor API
 * @module @cyclonedx/ui/sbom/utils/harborRequest
 */
import { CONFIG } from './constants'

type Params = {
  body?: Record<string, unknown>
  jwtToken?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  path: string
  signal?: AbortSignal
  children?: true | null
}

const harborRequest = async ({
  body,
  jwtToken,
  method = 'GET',
  path,
  signal = new AbortController().signal,
  children = true,
}: Params) => {
  // ensure path doesn't contain double slashes
  const url = new URL(`${CONFIG.API_URL}/v1/${path}`.replace(/\/\//g, '/'))

  if (children) {
    // append the children=true query param to the url
    url.searchParams.append('children', 'true')
  }

  // make the request and wait for the response
  const response = await fetch(url, {
    method,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `${jwtToken}`,
    },
    signal,
    body: body ? JSON.stringify(body) : null,
  })

  // if the response is not ok, throw an error
  if (!response.ok) {
    throw new Response(response.statusText, { status: response.status })
  }

  // return the response body
  return response.json()
}

export default harborRequest