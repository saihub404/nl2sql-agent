import httpx
import sys

def test_upload():
    with open("final_cleaned_dataset.csv", "rb") as f:
        print("Uploading file...")
        # read just a chunk if it's too big to load in memory all at once?
        # httpx supports streaming files
        response = httpx.post(
            "http://localhost:8000/api/upload",
            files={"file": ("final_cleaned_dataset.csv", f, "text/csv")},
            timeout=120
        )
        print(response.status_code)
        print(response.text)

if __name__ == "__main__":
    test_upload()
