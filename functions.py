tools = {
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "realtime_search",
        "description": "This function performs a real-time search on the web using the RapidAPI service. It takes in a query, a list of domains to search in, and the maximum number of results to return. It returns a list of snippets and corresponding URLs.",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "The search query"
            },
            "domains": {
              "type": "string",
              "description": "The domains to search in"
            },
            "max": {
              "type": "number",
              "description": "The maximum number of results to return"
            }
          },
          "required": ["query", "domains", "max"]
        }
      }
    }
  ]
}
