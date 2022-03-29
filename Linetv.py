import json
import logging
import os
import re
import subprocess

import rich.progress
import httpx
from lxml import etree

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
session = httpx.Client()
session.headers.update({'User-Agent': UA})


class Parser():
    def __init__(self, dramaid: str):
        self.dramaid = str(dramaid)
        self.html = session.get(f'https://www.linetv.tw/drama/{self.dramaid}')
        self.get_eps()
        self.get_behind()

    def get_eps(self):
        self.eps = []
        parser = etree.HTML(self.html.text)
        data = json.loads(parser.xpath('//head/script')[0].text[27:])
        for _ in data['entities']['dramaInfo']['byId'][self.dramaid]['eps_info']:
            self.eps.append(_['number'])

    def get_behind(self):
        self.behind = {}
        parser = etree.HTML(self.html.text)
        data = json.loads(parser.xpath(
            '//script[@type="application/ld+json"]')[2].text)
        for _trailer in data['trailer']:
            self.behind[_trailer['name']] = _trailer['contentUrl']


class DL:
    class Drama():
        def __init__(self, dramaid: str, ep: str, lng: str, subtitle=False, no_download=False):
            self.dramaid = dramaid
            self.subtitle = subtitle
            self.ep = ep
            self.lng = lng
            self.no_download = no_download
            self.new_old = True
            self.dramaname = ''
            self.keyId = ''
            self.keyType = ''
            self.m3u8 = ''
            self.sub_url = ''
            self.urlfix = ''
            self.video_url = []
            self.check_ffmpeg()
            self.get_part_url()
            self.get_m3u8()
            self.get_m3u8_key()
            self.dl_video()
            # shutil.rmtree('.')

        def check_ffmpeg(self):
            try:
                subprocess.Popen(
                    'ffmpeg -h', shell=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except FileNotFoundError:
                logging.info('本項目需要ffmpeg，請手動安裝ffmpeg')
                raise

        def get_part_url(self):
            req = session.get(
                f'https://www.linetv.tw/api/part/{self.dramaid}/eps/{self.ep}/part')
            try:
                parser = req.json()['epsInfo']['source'][0]['links'][0]
            except KeyError:
                logging.warning(req.json()['message'])
                return
            self.dramaname = req.json()['dramaInfo']['name']
            self.keyId = parser['keyId']
            self.keyType = parser['keyType']
            self.m3u8 = parser['link']
            if 'subtitle' in parser:
                self.sub_url = parser['subtitle']
            logging.debug('抓取Drama資料成功')

        def get_m3u8(self):
            self.urlfix = re.findall(r'(.*\/)\d+.*', self.m3u8)[0]
            self.dramaid, self.ep = re.findall(
                r'(\d*)\/(\d*)\/v\d', self.urlfix)[0]
            req = session.get(self.m3u8)
            try:
                url, self.res = re.findall(
                    r'((\d*)\/\d*-eps-\d*_\d*p\.m3u8.*)', req.text)[-1]
                self.new_old = True
            except IndexError:
                url, self.res = re.findall(
                    r'(\d*-eps-\d*_(\d*)p.\.m3u8.*)', req.text)[-1]
                self.new_old = False

            if self.new_old:
                m3u8url = f'{self.urlfix}{url}'
                m3u8 = session.get(m3u8url)
                m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                              f'{self.dramaid}-eps-{self.ep}_{self.res}p.key', m3u8.text)
                self.video_url.append(
                    f'{self.urlfix}{self.res}/' + re.findall(r"(.*\.ts.*)", m3u8)[0])
                m3u8 = re.sub(r'\?.*', '', m3u8)
                with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8'), 'w') as f:
                    f.write(m3u8)
            else:
                res = re.findall(r'(\d*-eps-\d*_\d*p_\.m3u8)', req.text)
                m3u8url = f'{self.urlfix}{self.dramaid}-eps-{self.ep}_{self.res}p_.m3u8'
                m3u8 = session.get(m3u8url)
                m3u8 = re.sub(r'https://keydeliver.linetv.tw/jurassicPark',
                              f'{self.dramaid}-eps-{self.ep}_{self.res}p.key', m3u8.text)
                for _ in re.findall(r'(\d*-eps-\d*_\d*p_\d*\.ts)', m3u8):
                    self.video_url.append(f'{self.urlfix}{_}')
                with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8'), 'w') as f:
                    f.write(m3u8)

        def get_m3u8_key(self):
            data = {'keyType': self.keyType, 'keyId': self.keyId,
                    'dramaId': int(self.dramaid), 'eps': int(self.ep)}
            req = session.post(
                'https://www.linetv.tw/api/part/dinosaurKeeper', json=data)
            token = req.json()['token']
            key = httpx.get(
                'https://keydeliver.linetv.tw/jurassicPark', headers={'authentication': token})
            with open(os.path.join('.', f'{self.dramaid}-eps-{self.ep}_{self.res}p.key'), 'wb') as f:
                f.write(key.content)

        def dl_video(self):
            if self.no_download:
                return

            logging.info(f'正在下載：{self.dramaname} 第{self.ep}集 {self.res}P')
            for _url in self.video_url:
                with open(os.path.basename(_url.split('?')[0]), 'ab') as download_file:
                    with httpx.stream("GET", _url) as response:
                        total = int(response.headers["Content-Length"])

                        with rich.progress.Progress(
                            "[progress.percentage]{task.percentage:>3.1f}%",
                            rich.progress.BarColumn(bar_width=50),
                            rich.progress.DownloadColumn(),
                            rich.progress.TransferSpeedColumn(),
                        ) as progress:
                            download_task = progress.add_task(
                                "Download", total=total)
                            for chunk in response.iter_bytes():
                                download_file.write(chunk)
                                progress.update(
                                    download_task, completed=response.num_bytes_downloaded)

            output = os.path.join('.', f'{self.dramaname}-E{self.ep}.mp4')
            ffmpeg_cmd = ['ffmpeg', '-loglevel', 'quiet', '-stats', '-allowed_extensions', 'ALL',
                          '-protocol_whitelist', 'http,https,tls,rtp,tcp,udp,crypto,httpproxy,file', '-y', '-i', f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8', '-movflags', '+faststart', '-c', 'copy']

            if self.lng:
                ffmpeg_cmd.extend(['-metadata:s:a:0', f'language={self.lng}'])
            ffmpeg_cmd.extend([output])
            logging.info('正在合併檔案')
            subprocess.Popen(ffmpeg_cmd).communicate()

            if not os.path.exists(output):
                logging.info('下載失敗')
                return
            else:
                logging.info('下載完成')

            if self.sub_url and self.subtitle:
                sub = session.get(self.sub_url)
                if sub.status_code != 200:
                    logging.info('正在下載字幕')
                    sub = session.get(
                        f'{self.urlfix}caption/{self.dramaid}-eps-{self.ep}.vtt')
                with open(f'{self.dramaname}-E{self.ep}.vtt', 'w', encoding='utf-8') as f:
                    f.write(sub.text)

            # subprocess.Popen(
            #     ['rclone', 'move', output, 'GD:', '-P']).communicate()
            for _ in self.video_url:
                os.remove(os.path.basename(_.split('?')[0]))
            os.remove(f'{self.dramaid}-eps-{self.ep}_{self.res}p.m3u8')
            os.remove(f'{self.dramaid}-eps-{self.ep}_{self.res}p.key')

    class Behind():
        def __init__(self, url: str, filename: str):
            logging.info(f'正在下載{filename}')
            video = session.get(url)
            videoname = filename + url.split('/')[-1][-4:]

            with open(videoname, 'wb') as f:
                f.write(video.content)

            if not os.path.exists(videoname):
                logging.info('下載失敗')
            else:
                logging.info('下載成功')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('--dramaid', '-id', help='輸入DramaId')
    parser.add_argument('--ep', help='輸入集數')
    parser.add_argument('--epall', help='一次下載全部集數', action="store_true")
    parser.add_argument('--special', '-sp',
                        help='一次下載全部幕後花絮和精華', action="store_true")
    parser.add_argument('--sub', help='若有字幕自動下載', action="store_true")
    parser.add_argument('--lng', help='輸入音軌語言')
    parser.add_argument('--no_download', help='僅下載m3u8和key',
                        action="store_true")
    parser.add_argument('--debug', help='除錯模式', action="store_true")
    args = parser.parse_args()

    if args.debug:
        logging.basicConfig(format='%(message)s', level=logging.DEBUG, handlers=[
                            logging.StreamHandler()])
    else:
        logging.basicConfig(format='%(message)s', level=logging.INFO)

    try:
        with open('config.json') as f:
            config = json.load(f)
        if config['access_token']:
            session.headers.update({'authorization': config['access_token']})
            logging.info('找到access_token，將採用登入模式下載')
    except:
        logging.info('找不到config.json，將採用未登入模式下載')

    if args.dramaid and args.special:
        sps = Parser(args.dramaid).behind
        for sp in sps:
            DL.Behind(sps[sp], sp)

    if args.dramaid and args.epall:
        for _ep in Parser(args.dramaid).eps:
            DL.Drama(args.dramaid, _ep, args.lng, args.sub, args.no_download)

    if args.dramaid and args.ep:
        if args.ep.find('-') != -1:
            ids = range(
                int(args.ep.split('-')[0]), int(args.ep.split('-')[1]) + 1)
        elif args.ep.find(',') != -1:
            ids = args.ep.split(',')
        else:
            ids = [args.ep]
        for _ep in ids:
            DL.Drama(args.dramaid, _ep, args.lng, args.sub, args.no_download)
