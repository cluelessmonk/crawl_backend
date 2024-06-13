from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func

Base = declarative_base()


class Job(Base):
    __tablename__ = 'jobs'

    job_id = Column(String(36), primary_key=True)
    job_name = Column(String)
    scheduler = Column(String)
    output = Column(String)
    crawler = Column(String)
    status = Column(String)
    last_run = Column(DateTime, nullable=True)
    created_by = Column(String)
    created_at = Column(DateTime, default=func.now())

    instances = relationship("JobInstance", back_populates="job")


class SourceCrawler(Base):
    __tablename__ = 'source_crawler'

    source_id = Column(String(36), primary_key=True)
    crawler_file_name = Column(String(100))
    is_create_new = Column(Integer)


class SourceData(Base):
    __tablename__ = 'source_data'

    source_id = Column(String(36), primary_key=True)
    source_name = Column(String(200))
    source_type = Column(String(200))


class SourceUrls(Base):
    __tablename__ = 'source_urls'

    source_id = Column(String(36), primary_key=True)
    url = Column(String(4000), primary_key=True)


class JobInstance(Base):
    __tablename__ = 'job_instances'

    instance_id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey('jobs.job_id'))
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    status = Column(String)
    log = Column(Text)
    previous_instance_id = Column(String(36), ForeignKey('job_instances.instance_id'))

    job = relationship("Job", back_populates="instances")
    previous_instance = relationship("JobInstance", remote_side=[instance_id])
    crawled_data = relationship("CrawledData", back_populates="job_instance")


class CrawledData(Base):
    __tablename__ = 'crawled_data'

    data_id = Column(Integer, primary_key=True)
    instance_id = Column(String(36), ForeignKey('job_instances.instance_id'))
    url = Column(String)
    raw_os_path = Column(String)
    scraped_os_path = Column(String)
    timestamp = Column(DateTime, default=func.now())

    job_instance = relationship("JobInstance", back_populates="crawled_data")


