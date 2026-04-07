import time
import json
import os
from typing import Callable
from fastapi import Request, Response
from fastapi.routing import APIRoute
from datetime import datetime

LOGS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

class TenantLoggingRoute(APIRoute):
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            # We must load the body so it can be read if needed by the route
            # and by the logger
            try:
                req_body = await request.body()
            except Exception:
                req_body = b""
                
            start_time = time.time()
            
            # Execute original handler
            try:
                response: Response = await original_route_handler(request)
            except Exception as e:
                # If an exception is raised before returning a Response, 
                # we still might want to log it, but FastAPI handles exceptions via ExceptionHandlers.
                # We'll re-raise it.
                raise e
            
            process_time = time.time() - start_time
            
            # Check if tenant_id was set by the dependencies
            tenant_id = getattr(request.state, "tenant_id", None)
            
            if tenant_id is not None:
                log_file_path = os.path.join(LOGS_DIR, f"tenant_{tenant_id}.log")
                
                try:
                    res_body = response.body
                    res_text = json.loads(res_body.decode()) # Try to format as json obj
                except Exception:
                    try:
                        res_text = getattr(response, "body", b"").decode()
                    except Exception:
                        res_text = "<binary or streaming response>"
                
                try:
                    req_text_decoded = req_body.decode()
                    req_text = json.loads(req_text_decoded) if req_text_decoded else {}
                except Exception:
                    req_text = "<binary request body>"
                
                log_data = {
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "method": request.method,
                    "url": str(request.url),
                    "process_time_s": round(process_time, 4),
                    "status_code": response.status_code,
                    "request_body": req_text,
                    "response_body": res_text
                }
                
                try:
                    with open(log_file_path, "a", encoding="utf-8") as f:
                        f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
                except Exception as ex:
                    print(f"Error writing to log file: {ex}")
            
            return response

        return custom_route_handler
