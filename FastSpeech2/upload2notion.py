import os
import mimetypes
import requests
import glob
from notion.client import NotionClient
from notion.block import ImageBlock, FileBlock

def build_operation(id, path, args, command="set", table="block"):
    """
    Data updates sent to the submitTransaction endpoint consist of a sequence of "operations". This is a helper
    function that constructs one of these operations.
    """

    if isinstance(path, str):
        path = path.split(".")

    return {"id": id, "path": path, "args": args, "command": command, "table": table}

def upload_file_to_row_property(client, row, path, property_name):
    mimetype = mimetypes.guess_type(path)[0] or "text/plain"
    filename = os.path.split(path)[-1]
    data = client.post("getUploadFileUrl", {"bucket": "secure", "name": filename, "contentType": mimetype}, ).json()
    # Return url, signedGetUrl, signedPutUrl
    mangled_property_name = [e["id"] for e in row.schema if e["name"] == property_name][0]
    with open(path, "rb") as f:
        response = requests.put(data["signedPutUrl"], data=f, headers={"Content-type": mimetype})
        response.raise_for_status()
    simpleurl = data['signedGetUrl'].split('?')[0]

    try:
        filelist = row.get('properties')[mangled_property_name]
        filelist.append([filename, [["a", simpleurl]]]) #append new file
    except:
        filelist = [[filename, [["a", simpleurl]]]]

    op1 = build_operation(id=row.id, path=["properties", mangled_property_name], args=filelist, table="block", command="set")
    file_id = simpleurl.split("/")[-2]
    op2 = build_operation(id=row.id, path=["file_ids"], args={"id": file_id}, table="block", command="listAfter")
    client.submit_transaction([op1, op2])

def upload_files_to_notion(path, name, iter, dataset, mel_len, sampling_rate, vocoder):
    token_v2 = 'd8be8ab093ce72b5a92c2825dbbf09ab3b5371a014f312fc491c54f38599c2acdfdcbe6a01abb9698fca33ee839e6936970e66c3de3b82fcfb002a93eab614348ad4d013ab9bf27addfe37517fdf'
    client = NotionClient(token_v2=token_v2)

    # 포스팅 목록 테이블 페이지
    table_url = 'https://www.notion.so/aipark/bfb80f17b1434d3eaf6ed535aa508dee?v=da0c07bb4201466f95dc624cc307899e'

    # 테이블 가져오기
    cv = client.get_collection_view(table_url)

    png_list = sorted(glob.glob(os.path.join(path, '*.png')))
    wav_list = sorted(glob.glob(os.path.join(path, '*.wav')))
    tg_list = sorted(glob.glob(os.path.join(path, '*.TextGrid')))

    # 카테고리 추가 후 파일 업로드
    row = cv.collection.add_row()
    row.set_property('title', name)
    row.set_property('Iteration', iter)
    row.set_property('Dataset', dataset)
    row.set_property('Mel_len', mel_len)
    row.set_property('Sampling rate', sampling_rate)
    row.set_property('Vocoder', vocoder)
    
    # Upload Images and Audios
    for wav, png, tg in zip(wav_list, png_list, tg_list):
        upload_file_to_row_property(client, row, wav, 'Audio')
        image = row.children.add_new(ImageBlock)
        image.upload_file(png)
        image.caption = png.split('/')[-1]
        text = row.children.add_new(FileBlock)
        text.upload_file(tg)


    

if __name__ == '__main__':
    p = './output/result/AUDIOBOX_44k_sp/330000'
    n = 'test'
    iter = 9999
    d = 'audiobox'
    m = '1000'
    sr = 44100
    v = 'hifi'
    
    upload_files_to_notion(p, n, iter, d, m, sr, v)
