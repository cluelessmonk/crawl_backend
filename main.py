from flask import Flask, request, jsonify, abort 
from flask_cors import CORS
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, Job, SourceCrawler, SourceData, SourceUrls, JobInstance, CrawledData
from datetime import datetime
from functions import scrape_page , crawl_urls
from flask import Flask, send_file, request, jsonify
import os
import zipfile
import io

app = Flask(__name__)
CORS(app, origins='http://localhost:3000')
from queues import crawl_queue, scrape_queue
import os
# Create an SQLite database
DATABASE_URL = 'sqlite:///crawlx.db'
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
BASE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CRAWLERS_DIR = os.path.join(os.getcwd(), 'crawlers')
# Create a configured "Session" class
Session = scoped_session(sessionmaker(bind=engine))


#mock data to send for stats
stats = {
    "numRunningInstance": 5,
    "numCrawledURLS": 100,
    "numScrapedURLS": 80,
    "numFailedTasks": 10
}


#------------------------------------------------------@@ ALL IMPORTS AND INITIALIZATION -^ @@---------------------------------

#Functionality BEGINS from here --

#------------------------------------------------------@@@ Managing Jobs API @@@------------------------------------------------------------------#



#code to manage the jobs for all requests
@app.route('/api/jobs', methods=['GET', 'POST'])
def manage_jobs():
    session = Session()
    if request.method == 'GET':
        jobs = session.query(Job).all()
        job_list = []
        for job in jobs:
            job_dict = {}
            for column in Job.__table__.columns:
                job_dict[column.name] = getattr(job, column.name)
            job_list.append(job_dict)
        return jsonify(job_list)

    if request.method == 'POST':
        data = request.json
        if 'last_run' in data:
            data['last_run'] = datetime.strptime(data['last_run'], '%Y-%m-%dT%H:%M:%S')
        new_job = Job(**data)
        session.add(new_job)
        session.commit()
        return jsonify({"message": "Job created successfully"})


@app.route('/api/jobs/<string:job_id>', methods=['GET', 'DELETE'])
def manage_job(job_id):
    session = Session()
    job = session.query(Job).get(job_id)

    if not job:
        return jsonify({"message": "Job not found"}), 404

    if request.method == 'GET':
        job_dict = {column.name: getattr(job, column.name) for column in Job.__table__.columns}
        return jsonify(job_dict)

    if request.method == 'DELETE':
        session.delete(job)
        session.commit()
        return jsonify({"message": "Job deleted successfully"})

#done till here



# below thing has a doubt so it needs to be resolved
#---------------------------------------------------------@@ JOb INSTANCES @@----------------------------------------------------------------------------------###


#Below function does two things , if it is GET it returns the instances associated with the job and if it is POST it 
# creates the instance and sends the instance to the respective queue based on either crawler or just scraping.
@app.route('/api/job-instances', methods=['GET', 'POST'])
def manage_job_instances():
    session = Session()
    if request.method == 'GET':
        print(request.args)
        instances = session.query(JobInstance).filter_by(job_id=request.args['job_id']).all()
        instances_list = []
        for instance in instances:
            instance_dict = {}
            for column in JobInstance.__table__.columns:
                instance_dict[column.name] = getattr(instance, column.name)
            instances_list.append(instance_dict)
        return jsonify(instances_list)

    if request.method == 'POST':
        data = request.json
        instances = session.query(JobInstance).filter_by(job_id=request.json['job_id']).filter_by(
            status='RUNNING').all()
        if len(instances) > 0:
            abort(412, description="Cannot create job instance as one instance is running!")
        source_id = data['source_id']
        data.pop('source_id')
        source_data = get_source_data(source_id)
        print(source_data.json)
        if 'start_time' in data:
            data['start_time'] = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M:%S')
        if 'end_time' in data:
            data['end_time'] = datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M:%S')
        new_instance = JobInstance(**data)
        session.add(new_instance)
        session.commit()

        if source_data.json['source_type'] == 'Custom URLs':
            print("The Source IS A CUSTOM URL\n")
            source_urls = get_source_urls(source_id)
            for url in source_urls.json:
                print(f" This is the URL user entered in source--'{url}' \n")
                scrape_queue.enqueue(scrape_page, url, request.json['instance_id'])
        else:
            print("The source is a crawler type source \n")
            crawl_queue.enqueue(crawl_urls, "https://careers.oracle.com/jobs/#en/sites/jobsearch/requisitions",
                                "oracle-jobs-crawler", data['instance_id'])
        return jsonify({"message": "Job instance created successfully"})


#below function returns the zip file that contains the scraped data of the scraped URLs
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
        download_name=f'{job_instance_id}.zip'  # Set the filename directly here
    )
    
 
    



#------------------------------------------------------@@@@ Crawled Data @@@@------------------------------------------------------------------#




#below one is done as well
@app.route('/api/crawled-metadata', methods=['POST'])
def get_crawled_metadata():
    session = Session()
    data = request.json
    instances = session.query(CrawledData).filter_by(instance_id=data['instance_id']).all()
    instances_list = []
    for instance in instances:
        instance_dict = {}
        for column in CrawledData.__table__.columns:
            instance_dict[column.name] = getattr(instance, column.name)
        instances_list.append(instance_dict)       
    return jsonify(instances_list)


@app.route('/enqueue', methods=['POST'])
def enqueue_task():
    task_type = request.form.get('task_type')
    url = request.form.get('url')
    crawler_name = request.form.get('crawler_name')
    if task_type.strip() == 'crawl':
        crawl_queue.enqueue(crawl_urls, url.strip(), crawler_name.strip(), "job-instance-id")
        return 'Crawl task enqueued successfully!'
    else:
        return 'Invalid task type'

@app.route('/api/crawler-file-content/<file_name>')
def get_file_content(file_name):
    file_path = os.path.join(CRAWLERS_DIR, file_name + ".py")
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            content = file.read()
        return jsonify({'content': content})
    else:
        return jsonify({'error': 'File not found'})

@app.route('/api/crawler-save_file', methods=['POST'])
def save_file():
    file_name = request.json['file_name'] + ".py"
    code = request.json['code']

    file_path = os.path.join(CRAWLERS_DIR, file_name)

    with open(file_path, 'w') as file:
        file.write(code)

    return jsonify({'message': 'File saved successfully'})





#------------------------------------------------------@@@@@@ Source Data @@@@@@@------------------------------------------------------------------#





# Create API endpoints for SourceData
@app.route('/api/source_data', methods=['POST'])
def create_source_data():
    session = Session()
    data = request.json

    # Check if source data with the same source_id already exists
    existing_source_data = session.query(SourceData).filter_by(source_id=data['source_id']).first()

    if existing_source_data:
        return jsonify({'message': 'Source Data already present'}), 409  # 409 Conflict status code

    # If not present, add the new source data
    source_data = SourceData(**data)
    session.add(source_data)
    session.commit()
    
    return jsonify({'message': 'Source Data created successfully'}), 201  # 201 Created status code


@app.route('/api/source_data', methods=['GET'])
def get_all_source_data():
    session = Session()
    source_data = session.query(SourceData).all()
    source_data_list = []
    for source in source_data:
        source_dict = {}
        for column in SourceData.__table__.columns:
            source_dict[column.name] = getattr(source, column.name)
        source_data_list.append(source_dict)
    return jsonify(source_data_list)

# Function to get source data
@app.route('/api/source_data/<source_id>', methods=['GET'])
def get_source_data(source_id):
    session = Session()
    source_data = session.query(SourceData).get(source_id)
    if source_data:
        source_dict = {column.name: getattr(source_data, column.name) for column in SourceData.__table__.columns}
        return jsonify(source_dict)
    return jsonify({"message": "Source Data not found"}), 404


#function to update the source data
@app.route('/api/source_data/<source_id>', methods=['PUT'])
def update_source_data(source_id):
    session = Session()
    data = request.json
    source_data = session.query(SourceData).get(source_id)
    if source_data:
        for key, value in data.items():
            setattr(source_data, key, value)
        session.commit()
        return jsonify({'message': 'Source Data updated successfully'})
    return jsonify({'message': 'Source Data not found'}), 404

#function to delete the provided source data
@app.route('/api/source_data/<source_id>', methods=['DELETE'])
def delete_source_data(source_id):
    session = Session()
    source_data = session.query(SourceData).get(source_id)
    if source_data:
        session.delete(source_data)
        session.commit()
        return jsonify({'message': 'Source Data deleted successfully'})
    return jsonify({'message': 'Source Data not found'}), 404





#------------------------------------------------------@@@@ Source URLS @@@@------------------------------------------------------------------#




#now we write the code for source urls endpoints

#insert new source data
@app.route('/api/source_urls', methods=['POST'])
def create_source_urls():
    session = Session()
    data = request.json
    source_id = data.get('source_id')
    url = data.get('url')
    
    # Check if the source_url already exists
    existing_source_url = session.query(SourceUrls).filter_by(source_id=source_id, url=url).first()
    if existing_source_url:
        return jsonify({'message': 'Source URL already exists'}), 409
    
    # If it does not exist, create a new one
    source_urls = SourceUrls(source_id=source_id, url=url)
    session.add(source_urls)
    session.commit()
    return jsonify({'message': 'Source URL created successfully'}), 201
  
# Function to fetch the source urls basis on source id
@app.route('/api/source_urls/<source_id>', methods=['GET'])
def get_source_urls(source_id):
    session = Session()
    source_urls = session.query(SourceUrls).filter_by(source_id=source_id).all()
    urls = [url.url for url in source_urls]
    session.close()  # Close the session after use
    return jsonify(urls)

#function to update the source urls
@app.route('/api/update_all_urls/<source_id>', methods=['POST'])
def update_all_urls(source_id):
    session = Session()
    new_urls = request.json.get('urls', [])

    try:
        # Delete all existing URLs for the source_id
        session.query(SourceUrls).filter_by(source_id=source_id).delete()
        session.commit()

        # Add new URLs
        for url in new_urls:
            new_url_record = SourceUrls(source_id=source_id, url=url)
            session.add(new_url_record)

        session.commit()
        return jsonify({'message': 'URLs updated successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'message': 'An error occurred', 'error': str(e)}), 500
    finally:
        session.close()




#------------------------------------------------------@@@@ Source Crawlers @@@@------------------------------------------------------------------#



#crawlers contain the python code to crawl website

#function to create the new source crawlers 
@app.route('/api/source_crawler', methods=['POST'])
def create_source_crawler():
    session = Session()
    data = request.json
    source_crawler = SourceCrawler(**data)
    session.add(source_crawler)
    session.commit()
    return jsonify({'message': 'Source Crawler created successfully'})

#function to create get source crawlers data based on their source id
@app.route('/api/source_crawler/<source_id>', methods=['GET'])
def get_source_crawler(source_id):
    session = Session()
    source_crawler = session.query(SourceCrawler).get(source_id)
    if source_crawler:
        return jsonify({column.name: getattr(source_crawler, column.name) for column in SourceCrawler.__table__.columns})
    return jsonify({'message': 'Source Crawler not found'}), 404



#function to update the source crawler data
@app.route('/api/source_crawler/<source_id>', methods=['PUT'])
def update_source_crawler(source_id):
    session = Session()
    data = request.json
    source_crawler = session.query(SourceCrawler).get(source_id)
    if source_crawler:
        for key, value in data.items():
            setattr(source_crawler, key, value)
        session.commit()
        return jsonify({'message': 'Source Crawler updated successfully'})
    return jsonify({'message': 'Source Crawler not found'}), 404



#function to delete the source crawler
@app.route('/api/source_crawler/<source_id>', methods=['DELETE'])
def delete_source_crawler(source_id):
    session = Session()
    source_crawler = session.query(SourceCrawler).get(source_id)
    if source_crawler:
        session.delete(source_crawler)
        session.commit()
        return jsonify({'message': 'Source Crawler deleted successfully'})
    return jsonify({'message': 'Source Crawler not found'}), 404

#----------------------------------------------------------@@ STATS DATA @@-----------------------------------------------------------#

@app.route('/api/stats', methods=['GET'])
def get_stats():
    return jsonify(stats)









#-----------------------------------------------------------@@ SERVER INITIALIZATIONS @@--------------------------------------------------------------#



# Starting the server on port 5001
if __name__ == '__main__':
    app.run(debug=True, port=5001)
