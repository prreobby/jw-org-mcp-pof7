import argparse, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
from jw_org_mcp.http_server import serve

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    serve(host=args.host, port=args.port)
