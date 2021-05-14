bsc_token_list_query = """
query MyQuery {
  ethereum(network: bsc) {
    transfers(options: {limitBy: {each: "currency.address", limit: 1}}) {
      currency {
        address
        symbol
      }
      count
    }
  }
}
"""
