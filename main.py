import requests
from tqdm import tqdm
from http import HTTPStatus
import configparser
import json


class VK:

    def __init__(self, access_token: str, user_id: str, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}
        self.base_url = 'https://api.vk.com/method/'
        self.photos_info = {}
    

    def get_users_info(self) -> json:
        url  = self.base_url + 'users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()


    def _generate_photo_name(self, likes_count: int, date_: str, ext='.jpg') -> str:
        name = str(likes_count) + ext
        if name in self.photos_info['names']:
            name = str(likes_count) + '_' + str(date_) + ext 
        return name  
    

    def _get_photos_amount(self):
        amount = 0
        while True:
            try:
                amount = int(input("Enter photos amount: "))
                if amount > 0:
                    return amount
                else:
                    print("Количество должно быть больше 0")
            except:
                print("Введено не число")


    def get_users_photos(self, owner_id: str, album_id='profile') -> bool:
        url = self.base_url + 'photos.get'
        photos_amount = self._get_photos_amount()
        params = {'owner_id': owner_id, 'album_id': album_id, 'rev': 0, 
                  'extended': 1, 'photo_sizes': 1, 'count': photos_amount}
        try:
            response = requests.get(url, params={**self.params, **params})
        except:
            print('Connection or another error occured!')
            return False
        if response.status_code == HTTPStatus.OK:
            try:
                all_info = response.json()
                self.photos_info['count'] = 0
                self.photos_info['names'] = []
                self.photos_info['items'] = []
                for item in all_info['response']['items']:
                    item_info = {}
                    item_info['date'] = item['date']
                    item_info['likes_count'] = item['likes']['count']
                    sizes_urls = {item['sizes'][i]['type']: item['sizes'][i]['url'] for i in range(len(item['sizes']))}
                    max_size = max(sizes_urls.keys()) if 'w' not in sizes_urls else 'w'
                    item_info['size'] = max_size
                    item_info['url'] = sizes_urls[max_size]
                    self.photos_info['items'].append(item_info)
                    self.photos_info['count'] += 1
                    self.photos_info['names'].append(self._generate_photo_name(item_info['likes_count'], item_info['date']))
                return True
            except:
                print('Failed while getting users photos!')
                print(all_info['error']['error_msg']) 
                return False 
        else:
            return False                              


class YaDisk:
    
    def __init__(self, access_token: str, version='v1'):
        self.token = access_token
        self.version = version
        self.base_url = 'https://cloud-api.yandex.net'
        self.active_folder = 'New_Folder'


    def _get_folder_name(self):
        folder_name = input('Enter folder name: ')
        return folder_name.replace('/', '')


    def create_folder(self) -> bool:
        url = self.base_url + f'/{self.version}/disk/resources'
        folder_name = self._get_folder_name()
        headers = {'Authorization': self.token}
        params = {'path': folder_name}
        try:
            response = requests.put(url, params=params, headers=headers)
        except:
            print('Error occured!')
            return False
        if response.status_code == HTTPStatus.CREATED:
            print('Folder successfully created!')
            self.active_folder = folder_name
            return True
        elif response.status_code == HTTPStatus.CONFLICT:
            self.active_folder = folder_name
            print("Folder already exist")
            return True
        else:
            print('Folder creation failed!')
            print(response.json()['description'])
            return False


    def upload_photo(self, photo_url: str, disk_path: str) -> bool:
        disk_url = self.base_url + f'/{self.version}/disk/resources/upload'
        headers = {'Authorization': self.token}
        params = {'url': photo_url,'path': disk_path, 'disable_redirects': 'false'}
        try:
            response = requests.post(disk_url, params=params, headers=headers)
        except:
            print('Uploading failed!')
            return False
        if response.status_code == HTTPStatus.ACCEPTED:
            return True
        else:
            return False
        

    def upload_all_photos(self, vk_user, folder_name: str) -> int:
        uploaded_files = 0
        if isinstance(vk_user, VK):
            photos_count = vk_user.photos_info['count']
            photo_links = [item['url'] for item in vk_user.photos_info['items']]
            print('Uploading files to yandex disk...')
            for i in tqdm(range(photos_count), colour='Green'):
                disk_path = folder_name + '/' + vk_user.photos_info['names'][i]
                if self.upload_photo(photo_links[i], disk_path):
                    uploaded_files += 1
            print('Done!')
            print('Number of uploaded files:', uploaded_files, '/', photos_count)
        return uploaded_files


def main():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    vk_user = VK(config['VK']['vk_token'], config['VK']['user_id'])
    yadisk_user = YaDisk(config['YaDisk']['yadisk_token'])
    if vk_user.get_users_photos(config['VK']['user_id']):
        if yadisk_user.create_folder():
            print(f"Do you want to upload to '{yadisk_user.active_folder}' directory?")
            answer = input("[Y] - yes, [_] - cancel: ").upper()
            if answer == "Y":
                yadisk_user.upload_all_photos(vk_user, yadisk_user.active_folder)
            else:
                print("Uploading was cancelled")
        with open('photos_info.json', 'w') as file:
            json.dump(vk_user.photos_info, file)


if __name__ == '__main__':
    main()
