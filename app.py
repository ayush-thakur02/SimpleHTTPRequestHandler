import http.server
import socketserver
import os
import json
import urllib.parse
from datetime import datetime
import cgi

class FileManagerHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        """Handle GET requests"""
        # Decode URL path to handle special characters
        decoded_path = urllib.parse.unquote(self.path)
        
        # Normalize path to prevent directory traversal
        path = os.path.normpath(self.translate_path(decoded_path))
        
        # Check if path is a directory
        if os.path.isdir(path):
            self.send_file_manager(path)
            return
        
        # For files, use the parent handler
        return http.server.SimpleHTTPRequestHandler.do_GET(self)

    def do_POST(self):
        """Handle file uploads"""
        try:
            # Parse the form data
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    'REQUEST_METHOD': 'POST',
                    'CONTENT_TYPE': self.headers['Content-Type'],
                }
            )

            # Get the file item
            if 'files[]' not in form:
                try:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b'No file was uploaded')
                except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError) as e:
                    print(f"Connection error while sending response: {e}")
                except Exception as e:
                    print(f"Unexpected error while sending response: {e}")
                return

            files = form['files[]']
            # Handle multiple files
            if not isinstance(files, list):
                files = [files]

            uploaded_files = []
            for fileitem in files:
                if fileitem.filename:
                    # Get the destination path
                    dest_path = self.translate_path(self.path)
                    file_path = os.path.join(dest_path, os.path.basename(fileitem.filename))
                    
                    # Save the file
                    with open(file_path, 'wb') as f:
                        f.write(fileitem.file.read())
                    
                    uploaded_files.append(fileitem.filename)

            # Send response
            try:
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'message': f'Successfully uploaded {len(uploaded_files)} files',
                    'files': uploaded_files
                }).encode())
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError) as e:
                print(f"Connection error while sending response: {e}")
            except Exception as e:
                print(f"Unexpected error while sending response: {e}")

        except Exception as e:
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': str(e)
                }).encode())
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError) as e:
                print(f"Connection error while sending error response: {e}")
            except Exception as e:
                print(f"Unexpected error while sending error response: {e}")

    def send_file_manager(self, path):
        """Send the file manager interface"""
        try:
            list = os.listdir(path)
        except OSError:
            try:
                self.send_error(404, "No permission to list directory")
            except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError) as e:
                print(f"Connection error while sending error response: {e}")
            except Exception as e:
                print(f"Unexpected error while sending error response: {e}")
            return None

        list.sort(key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
        
        # Generate table rows
        table_rows = self.generate_table_rows(path, list)
        
        # Get current time and user
        current_time = "2025-05-03 07:04:45"  # As specified
        username = "ayush-thakur02"  # As specified
        
        # Get full path for display
        abs_path = os.path.abspath(path)
        display_path = abs_path.replace(os.sep, ' / ')

        # Generate and send the HTML
        html = self.generate_html(current_time, username, abs_path, display_path, table_rows)
        encoded = html.encode('utf-8', 'replace')
        
        try:
            self.send_response(200)
            self.send_header("Content-type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except (ConnectionAbortedError, BrokenPipeError, ConnectionResetError) as e:
            print(f"Connection error while sending response: {e}")
        except Exception as e:
            print(f"Unexpected error while sending response: {e}")

    def generate_table_rows(self, path, list):
        # Fix parent directory navigation
        try:
            rel_path = os.path.relpath(path, os.getcwd())
        except ValueError:
            # Handle case when path and getcwd are on different drives
            rel_path = path
            
        # Get parent directory path
        parent_dir = os.path.dirname(rel_path)
        if parent_dir == '':
            parent_url = '/'
        else:
            parent_url = '/' + parent_dir.replace(os.sep, '/')
            
        table_rows = [f'''
            <tr>
                <td><a href="{urllib.parse.quote(parent_url)}"><i class="fas fa-arrow-up icon"></i> Parent Directory</a></td>
                <td>-</td>
                <td>-</td>
            </tr>
        ''']
        
        for name in list:
            fullname = os.path.join(path, name)
            displayname = name
            
            # Get file size
            try:
                size = os.path.getsize(fullname)
                if size < 1024:
                    size_str = f"{size} B"
                elif size < 1024*1024:
                    size_str = f"{size/1024:.1f} KB"
                else:
                    size_str = f"{size/(1024*1024):.1f} MB"
            except OSError:
                size_str = "N/A"
                
            # Get modification time
            try:
                mtime = os.path.getmtime(fullname)
                mtime_str = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except OSError:
                mtime_str = "N/A"
                
            # Update URL path construction
            url_path = os.path.join(
                os.path.relpath(path, os.getcwd()),
                name
            ).replace(os.sep, '/')
            
            if not url_path.startswith('/'):
                url_path = '/' + url_path
                
            # Add row to table with appropriate icon
            if os.path.isdir(fullname):
                icon = '<i class="fas fa-folder icon"></i>'
                displayname = name + "/"
                size_cell = "-"
            else:
                icon = '<i class="fas fa-file icon"></i>'
                size_cell = f'<span class="size-badge">{size_str}</span>'
            
            table_rows.append(f'''
                <tr>
                    <td><a href="{urllib.parse.quote(url_path)}">{icon}{displayname}</a></td>
                    <td>{size_cell}</td>
                    <td class="date-cell">{mtime_str}</td>
                </tr>
            ''')
        
        return '\n'.join(table_rows)

    def generate_html(self, current_time, username, abs_path, display_path, table_rows):
        return f'''
<!DOCTYPE html>
<html>
<head>
    <title>File Manager</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        :root {{
            --primary-color: #4f46e5;
            --hover-color: #4338ca;
            --background-color: #f9fafb;
            --card-background: #ffffff;
            --text-primary: #111827;
            --text-secondary: #6b7280;
            --border-color: #e5e7eb;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{ 
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: var(--background-color);
            color: var(--text-primary);
            line-height: 1.5;
        }}

        .container {{
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }}

        .card {{
            background: var(--card-background);
            border-radius: 1rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 
                       0 2px 4px -1px rgba(0, 0, 0, 0.06);
            padding: 2rem;
        }}

        .header {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid var(--border-color);
        }}

        .header-top {{
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .header h1 {{
            font-size: 1.875rem;
            font-weight: 700;
            color: var(--primary-color);
        }}

        .path-container {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        .current-path {{
            font-size: 0.875rem;
            color: var(--text-secondary);
            background: var(--background-color);
            padding: 0.75rem 1rem;
            border-radius: 0.5rem;
            flex-grow: 1;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}

        .upload-container {{
            position: relative;
            display: inline-block;
        }}

        .upload-button {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: var(--primary-color);
            color: white;
            padding: 0.75rem 1.5rem;
            border-radius: 0.5rem;
            cursor: pointer;
            font-weight: 500;
            transition: background-color 0.2s;
        }}

        .upload-button:hover {{
            background: var(--hover-color);
        }}

        #file-input {{
            display: none;
        }}

        .metadata {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 0.5rem;
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}

        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 0.5rem;
        }}

        th {{
            padding: 1rem;
            text-align: left;
            color: var(--text-secondary);
            font-weight: 600;
            font-size: 0.875rem;
            text-transform: uppercase;
        }}

        td {{
            padding: 1rem;
            background: var(--background-color);
            margin-bottom: 0.5rem;
        }}

        tr:not(:first-child) td:first-child {{
            border-top-left-radius: 0.5rem;
            border-bottom-left-radius: 0.5rem;
        }}

        tr:not(:first-child) td:last-child {{
            border-top-right-radius: 0.5rem;
            border-bottom-right-radius: 0.5rem;
        }}

        tr:not(:first-child):hover td {{
            background: #f3f4f6;
            transform: translateY(-1px);
            transition: all 0.2s ease;
        }}

        a {{
            color: var(--text-primary);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}

        a:hover {{
            color: var(--primary-color);
        }}

        .icon {{
            width: 20px;
            text-align: center;
            color: var(--primary-color);
        }}

        .size-badge {{
            display: inline-block;
            padding: 0.25rem 0.75rem;
            background: #e0e7ff;
            color: var(--primary-color);
            border-radius: 1rem;
            font-size: 0.875rem;
            font-weight: 500;
        }}

        .date-cell {{
            color: var(--text-secondary);
            font-size: 0.875rem;
        }}

        #upload-progress {{
            display: none;
            margin-top: 1rem;
            padding: 1rem;
            background: var(--background-color);
            border-radius: 0.5rem;
        }}

        .progress-bar {{
            width: 100%;
            height: 0.5rem;
            background: var(--border-color);
            border-radius: 0.25rem;
            margin-top: 0.5rem;
        }}

        .progress {{
            width: 0%;
            height: 100%;
            background: var(--primary-color);
            border-radius: 0.25rem;
            transition: width 0.3s ease;
        }}

        @media (max-width: 768px) {{
            .container {{
                margin: 1rem auto;
            }}
            
            .card {{
                padding: 1rem;
            }}

            th:nth-child(2), 
            td:nth-child(2) {{
                display: none;
            }}

            .path-container {{
                flex-direction: column;
                align-items: stretch;
            }}

            .upload-button {{
                width: 100%;
                justify-content: center;
            }}
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --primary-color: #818cf8;
                --hover-color: #6366f1;
                --background-color: #1f2937;
                --card-background: #111827;
                --text-primary: #f9fafb;
                --text-secondary: #9ca3af;
                --border-color: #374151;
            }}

            .size-badge {{
                background: #312e81;
            }}

            tr:not(:first-child):hover td {{
                background: #2d3748;
            }}
        }}

        .footer {{
            margin-top: 2rem;
                padding: 1rem;
                background: var(--card-background);
                border-radius: 1rem;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
                text-align: center;
                color: var(--text-secondary);
            }}

            .footer-content {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0 1rem;
            }}

            .footer-links {{
                display: flex;
                gap: 1rem;
            }}

            .footer-links a {{
                color: var(--text-secondary);
                text-decoration: none;
                transition: color 0.2s;
            }}

            .footer-links a:hover {{
                color: var(--primary-color);
            }}

            .footer-divider {{
                margin: 1rem 0;
                border: none;
                border-top: 1px solid var(--border-color);
            }}
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <div class="header">
                <div class="header-top">
                    <h1>File Manager</h1>
                    <div class="metadata">
                        <span><i class="far fa-clock"></i> {current_time}</span>
                        <span class="user" style="margin-left:10px"><i class="far fa-user"></i> {username}</span>
                    </div>
                </div>
                <div class="path-container">
                    <div class="current-path" title="{abs_path}">
                        <i class="fas fa-folder-open"></i> {display_path}
                    </div>
                    <div class="upload-container">
                        <label for="file-input" class="upload-button">
                            <i class="fas fa-cloud-upload-alt"></i>
                            Upload Files
                        </label>
                        <input type="file" id="file-input" multiple>
                    </div>
                </div>
                <div id="upload-progress">
                    <div id="upload-status">Uploading...</div>
                    <div class="progress-bar">
                        <div class="progress"></div>
                    </div>
                </div>
            </div>
            <table>
                <tr>
                    <th>Name</th>
                    <th>Size</th>
                    <th>Last Modified</th>
                </tr>
                {table_rows}
            </table>
        </div>
    </div>

    <!-- Add this right before the closing </div> of the container -->
    <div class="footer">
        <hr class="footer-divider">
        <div>
            <small>© 2025 File Manager. All rights reserved.</small>
        </div>
    </div>

    <script>
    document.getElementById('file-input').addEventListener('change', async function(e) {{
        const files = e.target.files;
        if (files.length === 0) return;

        const progressDiv = document.getElementById('upload-progress');
        const progressBar = document.querySelector('.progress');
        const statusDiv = document.getElementById('upload-status');
        
        progressDiv.style.display = 'block';
        let uploadedCount = 0;
        const totalFiles = files.length;
        
        try {{
            for (let i = 0; i < files.length; i++) {{
                const file = files[i];
                const formData = new FormData();
                formData.append('files[]', file);

                statusDiv.textContent = `Uploading ${{file.name}} (${{i + 1}}/${{totalFiles}})...`;
                
                const response = await fetch(window.location.href, {{
                    method: 'POST',
                    body: formData
            }});

                if (response.ok) {{
                    uploadedCount++;
                    const progress = (uploadedCount / totalFiles) * 100;
                    progressBar.style.width = `${{progress}}%`;
                    const result = await response.json();
                    console.log(`Uploaded ${{file.name}}:`, result);
                }} else {{
                    throw new Error(`Failed to upload ${{file.name}}: ${{response.statusText}}`);
                }}
            }}

            // All files uploaded successfully
            statusDiv.textContent = `Successfully uploaded ${{uploadedCount}} files! Reloading...`;
            
            // Force a complete reload from the server
            setTimeout(() => {{
                window.location.href = window.location.href;
            }}, 1000);

        }} catch (error) {{
            console.error('Upload error:', error);
            statusDiv.textContent = `Error: ${{error.message}}`;
            
            // Still allow reload after error
            setTimeout(() => {{
                window.location.href = window.location.href;
            }}, 2000);
        }}
    }});

    // Add auto-update for the server time
    function updateServerTime() {{
        const timeElements = document.querySelectorAll('.metadata span:first-child');
        timeElements.forEach(el => {{
            const time = new Date();
            const formattedTime = time.toISOString().replace('T', ' ').split('.')[0];
            el.innerHTML = `<i class="far fa-clock"></i> ${{formattedTime}}`;
        }});
    }}

    // Update time every second
    setInterval(updateServerTime, 1000);
    </script>
</body>
</html>
'''

def run(server_class=socketserver.TCPServer, handler_class=FileManagerHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Serving at port {port}")
    print(f"Open http://localhost:{port} or http://<your-ip>:{port}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
