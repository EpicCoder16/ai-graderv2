import mysql.connector
from mysql.connector import Error
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_connection():
    try:
        logger.info("Attempting to connect to MySQL database...")
        connection = mysql.connector.connect(
            host="127.0.0.1",
            user="ai_grader_user",
            password="eshwar",
            database="ai_grader",
            auth_plugin='mysql_native_password'
        )
        
        cursor = connection.cursor()
        try:
            # Check database exists
            cursor.execute("SHOW DATABASES")
            databases = cursor.fetchall()
            logger.info(f"Available databases: {databases}")
            
            if ('ai_grader',) not in databases:
                logger.error("Database 'ai_grader' does not exist!")
                return False
                
            # Check tables
            cursor.execute("USE ai_grader")
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            logger.info(f"Tables in ai_grader: {tables}")
            
            if not tables:
                logger.error("No tables found in ai_grader database!")
                return False
                
            # Check users table structure
            cursor.execute("DESCRIBE users")
            users_structure = cursor.fetchall()
            logger.info("Users table structure:")
            for column in users_structure:
                logger.info(f"  {column}")
                
            # Check comparisons table structure
            cursor.execute("DESCRIBE comparisons")
            comparisons_structure = cursor.fetchall()
            logger.info("Comparisons table structure:")
            for column in comparisons_structure:
                logger.info(f"  {column}")
                
            return True
            
        finally:
            cursor.close()
            connection.close()
            
    except Error as e:
        logger.error(f"Error connecting to MySQL: {e}")
        if "Access denied" in str(e):
            logger.error("Access denied. Please check username and password.")
        elif "Unknown database" in str(e):
            logger.error("Database does not exist. Please create the database first.")
        elif "Can't connect" in str(e):
            logger.error("Cannot connect to MySQL server. Is it running?")
        return False

if __name__ == "__main__":
    test_connection() 