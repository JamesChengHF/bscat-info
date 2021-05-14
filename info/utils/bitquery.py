from info.utils import fetch

bitquery_url = "https://graphql.bitquery.io/"


async def send_query(query):
    return await fetch.post(bitquery_url, data={'query': query})
