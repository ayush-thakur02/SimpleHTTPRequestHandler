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

    def do_PATCH(self):
        """Handle rename requests"""
        try:
            # Get request body
            content_length = int(self.headers['Content-Length'])
            body = self.rfile.read(content_length)
            data = json.loads(body)
            
            # Get the old and new paths
            old_path = self.translate_path(self.path)
            new_name = data.get('newName')
            
            if not new_name:
                self.send_error(400, "New name not provided")
                return
                
            # Create new path
            new_path = os.path.join(os.path.dirname(old_path), new_name)
            
            # Check if target already exists
            if os.path.exists(new_path):
                self.send_error(409, "File or folder with that name already exists")
                return
                
            try:
                os.rename(old_path, new_path)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'message': 'Item renamed successfully'
                }).encode())
            except OSError as e:
                self.send_error(500, f"Failed to rename: {str(e)}")
                
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

    def do_DELETE(self):
        """Handle delete requests"""
        try:
            # Get the path of the item to delete
            path = self.translate_path(self.path)
            
            if not os.path.exists(path):
                self.send_error(404, "File or folder not found")
                return
                
            try:
                if os.path.isdir(path):
                    os.rmdir(path)  # This will only delete empty directories
                else:
                    os.remove(path)
                    
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'success',
                    'message': 'Item deleted successfully'
                }).encode())
            except OSError as e:
                if os.path.isdir(path):
                    self.send_error(409, "Directory not empty or permission denied")
                else:
                    self.send_error(500, f"Failed to delete: {str(e)}")
                
        except Exception as e:
            self.send_error(500, f"Server error: {str(e)}")

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
        
        # Generate grid items
        grid_items = self.generate_grid_items(path, list)
        
        # Get current time and user
        current_time = "2025-05-03 07:04:45"  # As specified
        username = "ayush-thakur02"  # As specified
        
        # Get full path for display
        abs_path = os.path.abspath(path)
        display_path = abs_path.replace(os.sep, ' / ')

        # Generate and send the HTML
        html = self.generate_html(current_time, username, abs_path, display_path, grid_items)
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
        # Rename function but keep for compatibility
        return self.generate_grid_items(path, list)

    def generate_grid_items(self, path, list):
        # Fix parent directory navigation
        try:
            rel_path = os.path.relpath(path, os.getcwd())
        except ValueError:
            rel_path = path
            
        parent_dir = os.path.dirname(rel_path)
        parent_url = '/' + parent_dir.replace(os.sep, '/') if parent_dir else '/'
            
        grid_items = [f'''
            <div class="grid-item parent-dir">
                <div class="item-actions">
                    <button class="action-btn" disabled title="Parent directory cannot be modified">
                        <i class="fas fa-ellipsis-v"></i>
                    </button>
                </div>
                <a href="{urllib.parse.quote(parent_url)}">
                    <i class="fas fa-arrow-up icon"></i>
                    <span class="name">Parent Directory</span>
                </a>
            </div>
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
                
            url_path = os.path.join(
                os.path.relpath(path, os.getcwd()),
                name
            ).replace(os.sep, '/')
            
            if not url_path.startswith('/'):
                url_path = '/' + url_path
                
            if os.path.isdir(fullname):
                icon = '<i class="fas fa-folder icon"></i>'
                displayname = name + "/"
                size_info = ""
            else:
                icon = '<i class="fas fa-file icon"></i>'
                size_info = f'<span class="size-badge">{size_str}</span>'
            
            grid_items.append(f'''
                <div class="grid-item" data-path="{urllib.parse.quote(url_path)}">
                    <div class="item-actions">
                        <button class="action-btn" onclick="showActions(this)" title="More actions">
                            <i class="fas fa-ellipsis-v"></i>
                        </button>
                        <div class="action-menu">
                            <button onclick="renameItem('{displayname}', '{urllib.parse.quote(url_path)}')">
                                <i class="fas fa-edit"></i> Rename
                            </button>
                            <button onclick="deleteItem('{displayname}', '{urllib.parse.quote(url_path)}')">
                                <i class="fas fa-trash"></i> Delete
                            </button>
                        </div>
                    </div>
                    <a href="{urllib.parse.quote(url_path)}">
                        {icon}
                        <span class="name">{displayname}</span>
                        {size_info}
                        <span class="date">{mtime_str}</span>
                    </a>
                </div>
            ''')
        
        return '\n'.join(grid_items)

    def generate_html(self, current_time, username, abs_path, display_path, grid_items):
        # Update the HTML template to use grid instead of table
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
            text-decoration: none;
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

        .grid-container {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: 1rem;
            padding: 1rem 0;
        }}

        .grid-item {{
            background: var(--background-color);
            border-radius: 0.5rem;
            padding: 1rem;
            transition: all 0.2s ease;
            position: relative;
        }}

        .grid-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            background: #f3f4f6;
        }}

        .grid-item a {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            text-align: center;
        }}

        .grid-item .icon {{
            font-size: 2rem;
            margin-bottom: 0.5rem;
        }}

        .grid-item .name {{
            font-weight: 500;
            word-break: break-word;
        }}

        .grid-item .size-badge {{
            font-size: 0.75rem;
            padding: 0.25rem 0.5rem;
        }}

        .grid-item .date {{
            font-size: 0.75rem;
            color: var(--text-secondary);
        }}

        .item-actions {{
            position: absolute;
            top: 0.5rem;
            right: 0.5rem;
            opacity: 0;
            transition: opacity 0.2s;
        }}

        .grid-item:hover .item-actions {{
            opacity: 1;
        }}

        .action-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 0.25rem;
        }}

        .action-btn:hover {{
            background: var(--border-color);
        }}

        .action-menu {{
            position: absolute;
            top: 100%;
            right: 0;
            background: var(--card-background);
            border: 1px solid var(--border-color);
            border-radius: 0.5rem;
            padding: 0.5rem;
            display: none;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 100;
        }}

        .action-menu.show {{
            display: block;
        }}

        .action-menu button {{
            display: block;
            width: 100%;
            padding: 0.5rem 1rem;
            text-align: left;
            background: none;
            border: none;
            color: var(--text-primary);
            cursor: pointer;
            white-space: nowrap;
        }}

        .action-menu button:hover {{
            background: var(--background-color);
        }}

        #upload-progress {{
            display: none;
            margin-top: 1rem;
            padding: 1rem;
            background: var(--background-color);
            border-radius: 0.5rem;
        }}

        #upload-progress.show {{
            display: block;
        }}

        @media (prefers-color-scheme: dark) {{
            .grid-item:hover {{
                background: #2d3748;
            }}
        }}

        @media (max-width: 768px) {{
            .grid-container {{
                grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
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
            <div class="grid-container">
                {grid_items}
            </div>
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
        
        progressDiv.classList.add('show');
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
        }} finally {{
            setTimeout(() => {{
                progressDiv.classList.remove('show');
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

    function showActions(btn) {{
        const allMenus = document.querySelectorAll('.action-menu');
        allMenus.forEach(menu => menu.classList.remove('show'));
        btn.nextElementSibling.classList.add('show');
    }}

    // Close menus when clicking outside
    document.addEventListener('click', function(e) {{
        if (!e.target.closest('.item-actions')) {{
            document.querySelectorAll('.action-menu').forEach(menu => {{
                menu.classList.remove('show');
            }});
        }}
    }});

    async function deleteItem(name, path) {{
        if (confirm(`Are you sure you want to delete "${{name}}"?`)) {{
            try {{
                const response = await fetch(path, {{
                    method: 'DELETE'
                }});
                if (response.ok) {{
                    window.location.reload();
                }} else {{
                    alert('Failed to delete item');
                }}
            }} catch (error) {{
                console.error('Delete error:', error);
                alert('Failed to delete item');
            }}
        }}
    }}

    async function renameItem(name, path) {{
        const newName = prompt('Enter new name:', name);
        if (newName && newName !== name) {{
            try {{
                const response = await fetch(path, {{
                    method: 'PATCH',
                    headers: {{
                        'Content-Type': 'application/json'
                    }},
                    body: JSON.stringify({{ newName }})
                }});
                if (response.ok) {{
                    window.location.reload();
                }} else {{
                    alert('Failed to rename item');
                }}
            }} catch (error) {{
                console.error('Rename error:', error);
                alert('Failed to rename item');
            }}
        }}
    }}
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
