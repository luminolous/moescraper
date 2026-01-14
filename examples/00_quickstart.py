from moescraper import MoeScraperClient
from moescraper.adapters.demo import DemoAdapter

client = MoeScraperClient()
client.register(DemoAdapter())

posts = client.search(
    source="demo",
    tags=["catgirl", "blue_hair"],
    limit=20,
    nsfw=False,
    min_width=512,
)

client.save_metadata_jsonl(posts, "out/metadata.jsonl")
print("Saved posts:", len(posts))
print("First post:", posts[0])