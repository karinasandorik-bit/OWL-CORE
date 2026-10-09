"""Independent GitHub commit verifier; never writes to GitHub."""
import base64
import hashlib
import json
import os
import urllib.request

def verify(repo, branch, path, expected_sha256, expected_commit):
    token = os.environ["OWL_GITHUB_READ_TOKEN"]
    headers = {"Authorization":"Bearer "+token,"Accept":"application/vnd.github+json","User-Agent":"owl-independent-verifier/1"}
    def get(url):
        with urllib.request.urlopen(urllib.request.Request(url,headers=headers),timeout=15) as r:
            return json.load(r)
    root = "https://api.github.com/repos/"+repo
    # Compare immutable commit object and file content at that exact commit, not a moving branch.
    commit = get(root+"/commits/"+expected_commit)
    if commit["sha"] != expected_commit:
        raise ValueError("commit mismatch")
    obj = get(root+"/contents/"+path+"?ref="+expected_commit)
    actual = base64.b64decode(obj["content"].replace("\n",""))
    if hashlib.sha256(actual).hexdigest() != expected_sha256:
        raise ValueError("payload mismatch")
    return {"verified":True,"commit_sha":expected_commit,"blob_sha":obj["sha"],"payload_sha256":expected_sha256}

if __name__ == "__main__":
    import sys
    print(json.dumps(verify(*sys.argv[1:6])))
