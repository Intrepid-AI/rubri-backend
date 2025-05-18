import os
from datetime import datetime

from app.logger import get_logger
from app.constants import Constants

LOGGER = get_logger(__name__)


def make_directories(dir_list):
    for _dir_ in dir_list:
        if os.path.exists(_dir_):
            continue
        os.makedirs(_dir_)
        LOGGER.info("Directory {0} created".format(_dir_))

class Directory_Structure():
    '''This class will create the directory structure for the received data day wise'''

    date_today = None
    date_old = None
    todays_folder = None

    def __init__(self):
        pass

    def _isit_newday(self):
        '''This function will check if it is a new day or not'''
        today = datetime.now().date()
        
        if today != Directory_Structure.date_today:
        
            Directory_Structure.date_old = Directory_Structure.date_today
            Directory_Structure.date_today = today

            return True

        else:
        
            return False
        
    def _create_directory_for_newday(self):
        '''This function will create a directory for new day'''
        path = self._name_received_data_folder(Directory_Structure.date_today)
        make_directories([path])

        return path

    def _name_received_data_folder(self, dt):
        '''This function will name the folder for received data for passed date'''
        year,month,date = dt.strftime("%Y"), dt.strftime('%B_%Y'), dt.strftime('%d_%m_%Y')
        data = Constants.RECEIVED_DATA.value
        data_path = os.path.join(data,year,month,date)

        return data_path

    def __call__(self):
        '''This function will return the path for today's folder'''
        if self._isit_newday():
            LOGGER.info("New day detected")
            path = self._create_directory_for_newday()
            Directory_Structure.todays_folder = path
            return Directory_Structure.todays_folder

        else:

            return Directory_Structure.todays_folder


if __name__ == "__main__":
    # Test make_directories function
    test_dirs = ["test_dir1", "test_dir2"]
    print("Testing make_directories function...")
    make_directories(test_dirs)
    
    # Test Directory_Structure class
    print("\nTesting Directory_Structure class...")
    dir_struct = Directory_Structure()
    
    # Test directory creation for today
    today_path = dir_struct()
    print(f"Today's folder path: {today_path}")
    
    # Test if new day detection works
    is_new_day = dir_struct._isit_newday()
    print(f"Is it a new day? {is_new_day}")
    
    user_input = input("clean directories (y/n)?")

    if user_input == "y":
        # Clean up test directories
        for dir_name in test_dirs:
            if os.path.exists(dir_name):
                os.rmdir(dir_name)
            print(f"Cleaned up test directory: {dir_name}")

