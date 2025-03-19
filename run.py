import os
import sys
import uvicorn

if __name__ == "__main__":
    # Add the src directory to Python path
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

    uvicorn.run(
        "deal_data_extractor.main:app",
        host="0.0.0.0",
        port=1234,
        reload=True,
        reload_dirs=["src/deal_data_extractor"],
    )
