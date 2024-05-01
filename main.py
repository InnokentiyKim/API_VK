import requests
from tqdm import tqdm
from datetime import date
import configparser
import json


class VK:

    base_url = 'https://api.vk.com/method/'
    def __init__(self, access_token: str, user_id: str, version='5.131'):
        self.token= access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}
        self.photos_info = {}
    

    def get_users_info(self) -> json:
        url  = self.base_url + 'users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()


    def get_users_photos(self, owner_id: str, album_id='profile', rev=0, photo_sizes=1, count=5):
        url = self.base_url + 'photos.get'
        params = {'owner_id': owner_id, 'album_id': album_id, 'rev': rev, 
                  'extended': 1, 'photo_sizes': photo_sizes, 'count': count}
        try:
            response = requests.get(url, params={**self.params, **params})
            if 200 <= response.status_code < 300:
                return response
            else:
                return None
        except:
            print("Connection or another error occured!")


    def _generate_photo_name(self, likes_count: int, date_: str, ext='.jpg') -> str:
        name = str(likes_count) + ext
        if name in self.photos_info['names']:
            name = str(likes_count) + '_' + date_ + ext 
        return name  


    def get_photos_info(self, photos_get_resp: json) -> dict:
        self.photos_info['count'] = photos_get_resp['response']['count']
        self.photos_info['names'] = []
        if self.photos_info['count']:
            self.photos_info['album_id'] = photos_get_resp['response']['items'][0]['album_id']
            self.photos_info['items'] = []
            for item in photos_get_resp['response']['items']:
                item_info = {}
                item_info['date'] = date.fromtimestamp(item['date']).__str__()
                item_info['id'] = item['id']
                item_info['comments_count'] = item['comments']['count']
                item_info['reposts_count'] = item['reposts']['count']
                item_info['likes_count'] = item['likes']['count']
                item_info['user_likes'] = item['likes']['user_likes']
                item_info['size'] = {'height': item['sizes'][0]['height'], 'width': item['sizes'][0]['width']}
                item_info['url'] = item['sizes'][0]['url']
                for photo_size in item['sizes']:
                    if photo_size['height'] >= item_info['size']['height'] and photo_size['width'] >= item_info['size']['width']:
                        item_info['size']['height'] = photo_size['height']
                        item_info['size']['width'] = photo_size['width']
                        item_info['url'] = photo_size['url']
                self.photos_info['items'].append(item_info)
                self.photos_info['names'].append(self._generate_photo_name(item_info['likes_count'], item_info['date']))
        return self.photos_info


def create_folder_at_yadisk(access_token: str, folder_name: str, ver='v1') -> bool:
    base_url = 'https://cloud-api.yandex.net'
    url = base_url + f'/{ver}/disk/resources'
    headers = {'Authorization': access_token}
    params = {'path': folder_name}
    try:
        response = requests.put(url, params=params, headers=headers)
        if 200 <= response.status_code < 300:
            print('Folder successfully created!')
            return True
        else:
            print('Folder creation failed!')
            print(response.json()['description'])
            return False
    except:
        print('Folder creation failed!')
        return False


def upload_photo_to_yadisk(access_token: str, photo_url: str, disk_path: str, ver='v1', disable_redirects='false') -> bool:
    base_url = 'https://cloud-api.yandex.net'
    disk_url = base_url + f'/{ver}/disk/resources/upload'
    headers = {'Authorization': access_token}
    params = {'url': photo_url,'path': disk_path, 'disable_redirects': disable_redirects}
    try:
        response = requests.post(disk_url, params=params, headers=headers)
        if 200 <= response.status_code < 300:
            return True
        else:
            return False
    except:
        print('Uploading failed!')
        return False


def main():
    config = configparser.ConfigParser()
    config.read("settings.ini")
    vk_access_token = config['VK']['vk_token']
    user_id = config['VK']['user_id']
    yadisk_access_token = config['YaDisk']['yadisk_token']
    vk_user = VK(vk_access_token, user_id)
    get_photos_response = vk_user.get_users_photos(user_id)
    disk_folder_name = "VK_Photos"
    create_folder_at_yadisk(yadisk_access_token, disk_folder_name)
    if get_photos_response:
        try:
            get_photos_response = get_photos_response.json()
            photos_info = vk_user.get_photos_info(get_photos_response)
        except:
            print('Failed while getting users photos!')
            print('Error code: ', get_photos_response['error']['error_code'])
            print('Error message: ', get_photos_response['error']['error_msg'])
        else:
            files_count = vk_user.photos_info['count']
            uploaded_files_count = 0
            photo_links = [link['url'] for link in photos_info['items']]
            photo_names = vk_user.photos_info['names']
            print('Uploading files to yandex disk...')
            for i in tqdm(range(files_count), colour='Green'):
                disk_path = disk_folder_name + '/' + photo_names[i]
                if(upload_photo_to_yadisk(yadisk_access_token, photo_url=photo_links[i], disk_path=disk_path)):
                    uploaded_files_count += 1
            print('Done!')
            print('Number of uploaded files:', uploaded_files_count, '/', files_count)
            with open('photos_info.json', 'w') as file:
                json.dump(vk_user.photos_info, file)


if __name__ == '__main__':
    main()
