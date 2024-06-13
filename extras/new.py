from flask import Flask, send_file, request, jsonify
import os
import zipfile
import io

app = Flask(__name__)

# Get the current directory where this script is located
BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

@app.route('/download_job_instance_data/<job_instance_id>', methods=['POST'])
def download_job_instance_data(job_instance_id):
    # Construct the path to the job instance directory
    job_instance_path = os.path.join(BASE_DIRECTORY, job_instance_id)

    # Check if the directory exists
    if not os.path.exists(job_instance_path) or not os.path.isdir(job_instance_path):
        return jsonify({"error": "Job instance not found"}), 404

    # Create a zip file in memory
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(job_instance_path):
            for file in files:
                # Create a relative path to maintain folder structure in the zip file
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, job_instance_path)
                zf.write(file_path, arcname)
    
    memory_file.seek(0)

    # Send the zip file to the client
    return send_file(
        memory_file,
        mimetype='application/zip',
        as_attachment=True,
        attachment_filename=f'{job_instance_id}.zip'
    )

if __name__ == '__main__':
    app.run(debug=True)
