import mysql.connector
from mysql.connector import Error
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_connection():
    try:
        logger.info("Attempting to connect to MySQL database...")
        connection = mysql.connector.connect(
            host=os.getenv("MYSQL_HOST", "127.0.0.1"),  # Default to localhost if not set
            user=os.getenv("MYSQL_USER", "ai_grader_user"),
            password=os.getenv("MYSQL_PASSWORD", "eshwar"),
            database=os.getenv("MYSQL_DATABASE", "ai_grader"),
            auth_plugin='mysql_native_password'
        )
        
        # Test the connection and verify database structure
        cursor = connection.cursor()
        try:
            # Check if users table exists and has correct structure
            cursor.execute("""
                SELECT COLUMN_NAME, DATA_TYPE 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_SCHEMA = 'ai_grader' 
                AND TABLE_NAME = 'users'
            """)
            columns = cursor.fetchall()
            logger.info(f"Users table columns: {columns}")
            
            # Check if comparisons table exists
            cursor.execute("""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'ai_grader' 
                AND TABLE_NAME = 'comparisons'
            """)
            comparisons_exists = cursor.fetchone()[0] > 0
            logger.info(f"Comparisons table exists: {comparisons_exists}")
            
        finally:
            cursor.close()
        
        logger.info("Successfully connected to MySQL database")
        return connection
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        if "Access denied" in str(e):
            logger.error("Access denied. Please check username and password.")
        elif "Unknown database" in str(e):
            logger.error("Database does not exist. Please create the database first.")
        elif "Can't connect" in str(e):
            logger.error("Cannot connect to MySQL server. Is it running?")
        raise
