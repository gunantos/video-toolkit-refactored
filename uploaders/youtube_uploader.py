import os
import yaml
import logging
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class YouTubeUploader:
    def __init__(self, config_path='config/youtube_config.yaml'):
        self.config = self._load_config(config_path)
        self.creds = None
        self.service = None
        self._authenticate()

    def _load_config(self, path):
        with open(path, 'r') as f:
            return yaml.safe_load(f)

    def _authenticate(self):
        creds_path = self.config['youtube']['token_file']
        scopes = self.config['youtube']['scopes']
        client_id = self.config['youtube']['client_id']
        client_secret = self.config['youtube']['client_secret']
        redirect_uri = self.config['youtube']['redirect_uri']

        if os.path.exists(creds_path):
            self.creds = Credentials.from_authorized_user_file(creds_path, scopes)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(
                    {
                        "installed": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "redirect_uris": [redirect_uri],
                            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                            "token_uri": "https://oauth2.googleapis.com/token"
                        }
                    },
                    scopes=scopes
                )
                self.creds = flow.run_local_server(port=8080)

            with open(creds_path, 'w') as token_file:
                token_file.write(self.creds.to_json())

        self.service = build('youtube', 'v3', credentials=self.creds)

    def upload_video(self, video_file, title, description='', tags=None, categoryId='22', privacyStatus='private'):
        if tags is None:
            tags = []
        body = {
            'snippet': {
                'title': title,
                'description': description,
                'tags': tags,
                'categoryId': categoryId
            },
            'status': {
                'privacyStatus': privacyStatus
            }
        }

        media = MediaFileUpload(video_file, chunksize=-1, resumable=True)
        request = self.service.videos().insert(
            part=','.join(body.keys()),
            body=body,
            media_body=media
        )

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                logging.info(f"Uploading: {int(status.progress() * 100)}%")

        logging.info(f"Upload selesai: https://youtu.be/{response['id']}")
        return response['id']

# Contoh penggunaan:
#if __name__ == '__main__':
#    uploader = YouTubeUploader('config/youtube_config.yaml')
#    video_id = uploader.upload_video('path/to/video.mp4', 'Judul Video', 'Deskripsi video', ['tag1', 'tag2'])
#    print(f"Video uploaded with ID: {video_id}")
