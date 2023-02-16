# encoding:utf-8

"""
WechatEnterprise channel
"""
from channel.channel import Channel
from concurrent.futures import ThreadPoolExecutor
from common.log import logger
from config import conf
import json
import requests
import io
from wechatpy.enterprise.crypto import WeChatCrypto
from wechatpy.enterprise import WeChatClient
from wechatpy.exceptions import InvalidSignatureException
from wechatpy.enterprise.exceptions import InvalidCorpIdException
from wechatpy.enterprise import parse_message
from flask import Flask, request ,abort

thread_pool = ThreadPoolExecutor(max_workers=8)
app = Flask(__name__)

class WechatChannel(Channel):
    def __init__(self):
        pass

    def startup(self):
        # start message listener
        app.run(host='0.0.0.0',port=8888)
      
        
        

    def send(self, msg, receiver):
        logger.info('[WXCOM] sendMsg={}, receiver={}'.format(msg, receiver))
        CorpId = conf().get('WECHAT_CORP_ID')
        Secret = conf().get('Secret')
        AppId = conf().get('AppId')
        client = WeChatClient(CorpId, Secret,AppId)
        client.message.send_text(AppId,receiver,msg)

    def _do_send(self, query, reply_user_id):
        try:
            if not query:
                return
            context = dict()
            context['from_user_id'] = reply_user_id
            reply_text = super().build_reply_content(query, context)
            if reply_text:
                self.send(reply_text, reply_user_id)
        except Exception as e:
            logger.exception(e)

    @app.route('/wechat', methods=['GET','POST'])
    def handle(self, msg):
        query_params = request.args
        signature = query_params.get('msg_signature', '')
        timestamp = query_params.get('timestamp', '')
        nonce = query_params.get('nonce', '')    
        TOKEN = conf().get('WECHAT_TOKEN')
        EncodingAESKey = conf().get('WECHAT_ENCODING_AES_KEY')
        CorpId = conf().get('WECHAT_CORP_ID')
        crypto = WeChatCrypto(TOKEN, EncodingAESKey, CorpId)
        Secret = conf().get('Secret')
        AppId = conf().get('AppId')
        client = WeChatClient(CorpId, Secret,AppId)
        if request.method == 'GET':
            # 处理验证请求
            echostr = query_params.get('echostr', '')
            try:
                echostr = crypto.check_signature(signature, timestamp, nonce, echostr)
            except InvalidSignatureException:
                abort(403)
            print(echostr)
            return echostr
        elif request.method == 'POST':
            try:
                message = crypto.decrypt_message(
                    request.data,
                    signature,
                    timestamp,
                    nonce
                )
            except (InvalidSignatureException, InvalidCorpIdException):
                abort(403)
            msg = parse_message(message)
            if msg.type == 'text':
                reply = '收到，思考中...'
                thread_pool.submit(_do_send, msg.content, msg.source)
            else:
                reply = 'Can not handle this for now'
            client.message.send_text(AppId,msg.source,reply)
            return 'success'
