import re
import json
import http.client
from urllib.parse import urlparse, urlencode
from urllib.request import Request, urlopen, HTTPError, URLError

class LanzouDownloader:
    USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0'
    ALTERNATIVE_URLS = [
        'https://www.lanzoub.com/',
        'https://www.lanzouc.com/', 
        'https://www.lanzoue.com/', 
        'https://www.lanzouf.com/', 
        'https://www.lanzouh.com/', 
        'https://www.lanzoui.com/', 
        'https://www.lanzouj.com/', 
        'https://www.lanzouk.com/', 
        'https://www.lanzoum.com/', 
        'https://www.lanzoup.com/', 
        'https://www.lanzouv.com/', 
        'https://www.lanzouw.com/', 
        'https://www.lanzoux.com/', 
        'https://www.lanzouy.com/']

    def __init__(self):
        pass

    def get_direct_link(self, url: str) -> str:
        if not url:
            return json.dumps({'code': 400, 'msg': '请输入URL'}, ensure_ascii=False, indent=4)

        url_path = url.split('.com/')[1]
        for base_url in [ 'https://www.lanzoup.com/', *self.ALTERNATIVE_URLS]:
            full_url = base_url + url_path
            try:
                soft_info = self._curl_get(full_url)
            except (HTTPError, URLError) as e:
                continue  # 如果请求失败，则尝试下一个备用网址
            except Exception as e:
                return json.dumps({'code': 500, 'msg': f'内部错误: {str(e)}'}, ensure_ascii=False, indent=4)

            if "文件取消分享了" in soft_info:
                return json.dumps({'code': 400, 'msg': '文件取消分享了'}, ensure_ascii=False, indent=4)

            soft_name = re.findall(r'style="font-size: 30px;text-align: center;padding: 56px 0px 20px 0px;">(.*?)</div>', soft_info)
            if not soft_name:
                soft_name = re.findall(r'<div class="n_box_3fn".*?>(.*?)</div>', soft_info)
            soft_filesize = re.findall(r'<div class="n_filesize".*?>大小：(.*?)</div>', soft_info)
            if not soft_filesize:
                soft_filesize = re.findall(r'<span class="p7">文件大小：</span>(.*?)<br>', soft_info)
            if not soft_name:
                soft_name = re.findall(r'var filename = \'(.*?)\';', soft_info)
            if not soft_name:
                soft_name = re.findall(r'div class="b"><span>(.*?)</span></div>', soft_info)

            if "function down_p(){" in soft_info:
                return json.dumps({'code': 400, 'msg': '请输入分享密码'}, ensure_ascii=False, indent=4)

            link = re.findall(r'\n<iframe.*?name="[\s\S]*?"\ssrc="/(.*?)"', soft_info)
            if not link:
                link = re.findall(r'<iframe.*?name="[\s\S]*?"\ssrc="/(.*?)"', soft_info)

            if not link:
                continue

            ifurl = base_url + link[0]
            soft_info = self._curl_get(ifurl)
            segment = re.findall(r"'sign':'(.*?)'", soft_info)

            post_data = {
                "action": 'downprocess',
                "signs": "?ctdf",
                "sign": segment[0],
            }
            soft_info = self._curl_post(post_data, "https://www.lanzoup.com/ajaxm.php", ifurl)
            soft_info = json.loads(soft_info)

            if soft_info['zt'] != 1:
                return json.dumps({'code': 400, 'msg': soft_info['inf']}, ensure_ascii=False, indent=4)

            down_url1 = soft_info['dom'] + '/file/' + soft_info['url']
            down_url2 = self._curl_head(down_url1)

            down_url = down_url2 if down_url2 else down_url1

            return json.dumps({'code': 200, 'msg': '解析成功', 'name': soft_name[0] if soft_name else "", 'filesize': soft_filesize[0] if soft_filesize else "", 'downUrl': down_url}, ensure_ascii=False, indent=4)

        return json.dumps({'code': 404, 'msg': '无法解析链接'}, ensure_ascii=False, indent=4)

    def _curl_get(self, url: str, user_agent: str = '') -> str:
        request = Request(url)
        if user_agent:
            request.add_header('User-Agent', user_agent)
        else:
            request.add_header('User-Agent', self.USER_AGENT)
        response = urlopen(request)
        return response.read().decode()

    def _curl_post(self, post_data: dict, url: str, referer: str = '', user_agent: str = '') -> str:
        headers = {'User-Agent': user_agent or self.USER_AGENT, 'Referer': referer}
        data = urlencode(post_data).encode()
        request = Request(url, data=data, headers=headers)
        response = urlopen(request)
        return response.read().decode()

    def _curl_head(self, url: str) -> str:
        parsed_url = urlparse(url)
        conn = http.client.HTTPConnection(parsed_url.netloc)
        conn.request("HEAD", parsed_url.path)
        response = conn.getresponse()
        conn.close()
        return response.getheader('Location', '')
