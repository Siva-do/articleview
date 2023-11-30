import json
import math

import pandas as pd
import os
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup
import calendar
import requests
from dateutil.parser import parse


''' Request Functions starts '''


def status_log(r):
    """Pass response as a parameter to this function"""
    url_log_file = 'url_log.txt'
    if not os.path.exists(os.getcwd() + '\\' + url_log_file):
        with open(url_log_file, 'w') as f:
            f.write('url, status_code\n')
    with open(url_log_file, 'a') as file:
        file.write(f'{r.url}, {r.status_code}\n')


def sup_sub_encode(html):
    """Encodes superscript and subscript tags"""
    encoded_html = html.replace('<sup>', 's#p').replace('</sup>', 'p#s').replace('<sub>', 's#b').replace('</sub>',
                                                                                                         'b#s') \
        .replace('<Sup>', 's#p').replace('</Sup>', 'p#s').replace('<Sub>', 's#b').replace('</Sub>', 'b#s')
    encoded_html = BeautifulSoup(encoded_html, 'html.parser').text.strip()
    return encoded_html


def sup_sub_decode(html):
    """Decodes superscript and subscript tags"""
    decoded_html = html.replace('s#p', '<sup>').replace('p#s', '</sup>').replace('s#b', '<sub>').replace('b#s',
                                                                                                         '</sub>')
    # decoded_html = BeautifulSoup(decoded_html, 'html.parser')
    return decoded_html


def retry(func, retries=3):
    """Decorator function"""
    retry.count = 0

    def retry_wrapper(*args, **kwargs):
        attempt = 0
        while attempt < retries:
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                attempt += 1
                total_time = attempt * 10
                print(f'Retrying {attempt}: Sleeping for {total_time} seconds, error: ', e)
                time.sleep(total_time)
            if attempt == retries:
                retry.count += 1
                url_log_file = 'url_log.txt'
                if not os.path.exists(os.getcwd() + '\\' + url_log_file):
                    with open(url_log_file, 'w') as f:
                        f.write('url, status_code\n')
                with open(url_log_file, 'a') as file:
                    file.write(f'{args[0]}, requests.exceptions.ConnectionError\n')
            if retry.count == 3:
                print("Stopped after retries, check network connection")
                raise SystemExit

    return retry_wrapper


def abstract_cleaner(abstract):
    """Converts all the sup and sub script when passing the abstract block as html"""
    conversion_tags_sub = BeautifulSoup(str(abstract), 'lxml').find_all('sub')
    conversion_tags_sup = BeautifulSoup(str(abstract), 'lxml').find_all('sup')
    abstract_text = str(abstract).replace('<.', '< @@dot@@')
    for tag in conversion_tags_sub:
        original_tag = str(tag)
        key_list = [key for key in tag.attrs.keys()]
        for key in key_list:
            del tag[key]
        abstract_text = abstract_text.replace(original_tag, str(tag))
    for tag in conversion_tags_sup:
        original_tag = str(tag)
        key_list = [key for key in tag.attrs.keys()]
        for key in key_list:
            del tag[key]
        abstract_text = abstract_text.replace(original_tag, str(tag))
    abstract_text = sup_sub_encode(abstract_text)
    abstract_text = BeautifulSoup(abstract_text, 'lxml').text
    abstract_text = sup_sub_decode(abstract_text)
    abstract_text = re.sub('\s+', ' ', abstract_text)
    text = re.sub('([A-Za-z])(\s+)?(:|\,|\.)', r'\1\3', abstract_text)
    text = re.sub('(:|\,|\.)([A-Za-z])', r'\1 \2', text)
    text = re.sub('(<su(p|b)>)(\s+)(\w+)(</su(p|b)>)', r'\3\1\4\5', text)
    text = re.sub('(<su(p|b)>)(\w+)(\s+)(</su(p|b)>)', r'\1\3\5\4', text)
    text = re.sub('(<su(p|b)>)(\s+)(\w+)(\s+)(</su(p|b)>)', r'\3\1\4\6\5', text)
    abstract_text = re.sub('\s+', ' ', text)
    abstract_text = abstract_text.replace('< @@dot@@', '<.')
    return abstract_text.strip()


@retry
def post_json_response(url, headers=None, payload=None):
    """Returns the json response of the page when given with the url and headers"""
    ses = requests.session()
    r = ses.post(url, headers=headers, json=payload)
    if r.status_code == 200:
        return r.json()
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = ses.post(url, headers=headers, data=payload)  # your request get or post
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                # data_ = decode_base64(r.text)
                return r.json()
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def get_json_response(url, headers=None):
    """Returns the json response of the page when given with the of an url and headers"""
    r = requests.get(url, headers=headers)
    if r.status_code == 200:
        data_ = r.json()
        return data_
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.get(url, headers=headers)  # your request get or post
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                data_ = r.json()
                return data_
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def post_soup(url, headers=None, payload=None):
    '''returns the soup of the page when given with the of an url and headers'''
    refer = r'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status#server_error_responses'
    r = requests.Session().post(url, headers=headers, json=payload, timeout=30)
    r.encoding = r
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, features="xml")
        return soup
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.Session().post(url, headers=headers, data=payload)  # your request get or post
            r.encoding = r
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                return soup
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


@retry
def get_soup(url, headers=None):
    '''returns the soup of the page when given with the of an url and headers'''
    refer = r'https://developer.mozilla.org/en-US/docs/Web/HTTP/Status#server_error_responses'
    r = requests.Session().get(url, headers=headers, timeout=60)
    r.encoding = r.apparent_encoding
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        return soup
    elif 499 >= r.status_code >= 400:
        print(f'client error response, status code {r.status_code} \nrefer: {r.url}')
        status_log(r)
    elif 599 >= r.status_code >= 500:
        print(f'server error response, status code {r.status_code} \nrefer: {r.url}')
        count = 1
        while count != 10:
            print('while', count)
            r = requests.Session().get(url, headers=headers, timeout=60)  # your request get or post
            r.encoding = r.apparent_encoding
            print('status_code: ', r.status_code)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                return soup
                # print('done', count)
            else:
                print('retry ', count)
                count += 1
                # print(count * 2)
                time.sleep(count * 2)
    else:
        status_log(r)
        return None


def strip_it(text):
    return re.sub(r"\s+", ' ', text).strip()


def write_visited_log(url):
    with open(f'Visited_urls.txt', 'a', encoding='utf-8') as file:
        file.write(f'{url}\n')


def read_log_file():
    if os.path.exists('Visited_urls.txt'):
        with open('Visited_urls.txt', 'r', encoding='utf-8') as read_file:
            return read_file.read().split('\n')
    return []

def separate_affiliation(name):
    degree_list = ['NREMT', 'WCC', 'SFEM', 'CRNP', 'NEA-BC', 'LEED AP BD+C', 'FRANZCOG', 'MSCP', 'FRCR', 'M.A',
                   'ADCES(CDE)', 'B BioMed(Hons)', 'PGD', 'EsD', 'CNRN', 'B.MOS', 'FRSSDI', 'GCS', 'MCN', 'R.Ph',
                   'FNP-BC', 'CBN', 'MGC', 'PYG', 'BAO', 'HBSc', 'LDTC', 'MSCS', 'DACVO', 'FFSMB', 'PHC', 'MSI',
                   'PAC', 'PH.D.', 'TX', 'B.A.&Sc', 'LATG', 'CPE', 'RACS', 'B.S', 'MSAM', 'DABR', 'FACOG', 'RGDip',
                   'FRAC', 'SPT', 'SANE-A', 'CPN', 'MRCS', 'PES-NASM', 'FIMC', 'FAARC', 'FACHE', 'CHPN', 'MSIS', 'ONC',
                   'COL', 'HSP', 'FACS', 'OT/L', 'CAPT', 'MBBCH', 'D.N.C.C.M.', 'MM', 'AOCNS', 'FAMIA', 'MRC', 'FAANP',
                   'MSPT', 'MAEd', 'BCBA-D', 'LISW', 'RPAC', 'RPYT', 'BCS-CL', 'DHEd', 'FACOI', 'NPD-BC', 'APD',
                   'FACOS', 'PA', 'retired LEO/FF/Medic', 'CZT', 'ABD', 'FACOOG', 'MIS', 'MAMSE', 'FTOS', 'THM', 'RPh',
                   'UNDERGADUATE STUDENT', 'MHC', 'LLM', 'ME', 'BCC', 'AD', 'NP-C', 'CDR', 'BChir', 'RPVI', 'FRSA',
                   'BSc (Hons)', 'DABPMR', 'NPD/RN-BC', 'ARCPA (Hon.)', 'M.Med (Int.Medicine)', 'MHPE FACLP',
                   'WACP (PAED)', 'FAzPA', 'FRCPE', 'M.P.H', 'CEDCAT-S', 'F.R.C.P(Edin)', 'FFPM', 'CMSRN', 'MRCPCH',
                   'Md', 'DSci', 'MFCM', 'MLIS', 'QPI', 'APRN-BC', 'CARN', 'BScPharm', 'MSMED', 'pre-BS', 'BSB.E',
                   'CAQSM', 'FAAP', 'BSBA', 'LMHC', 'MStat', 'MBA', 'FFICM', 'NHA', 'MN', 'MSOT', 'CHFN', 'P.A',
                   'MBBChBAO', 'CGP', 'CIT', 'PH', 'DA', 'CDN', 'MBBS', 'DABMA', 'BPharm', 'MDCM',
                   'FICMS Adult Endocrinology', 'CDP', 'DCH(Edin)', 'GradCertClinT(R)', 'RCYT, PATH', 'SSGB', 'BCH',
                   'PhD', 'FICS', 'IQCI', 'RN-BC', 'CPA', 'CCC-A', 'LP', 'CCRN-K', 'CCC/slp .CCISM', 'Ph.D', 'LATg',
                   'AGCNS-BC', 'LPCC', 'DPS FACLP DFAPA FASM', 'DACVIM', 'FRCP(c)', 'NBC-HWC', 'DCH', 'HTLASCP',
                   'ACSM-EP', 'DMSC', 'MUP', 'PE-Eng', 'BCPS', 'MComMed', '(MS)', 'FCPath (Chem)', 'EDM', 'EMT',
                   'Mch', 'FAPTA', 'MRCP (Diab&Endo)', 'FNB', 'AAHIVS', 'BSBE', 'CLSSBB', 'FACP', 'FACOFP', 'FHRS',
                   'LCAS', 'CDCES', 'M.H.C.I', 'M.Tech', 'MMedEd', 'CKRT', 'VetMB CertAVP(EM) DipECEIM PhD MRCVS',
                   'FCAHS', 'OTS', 'CBTP', 'BCGP', 'FRCSCTH', 'D.A.A.E.T.S.', 'OCS', 'BSc (Hons), MScR', 'FACR', 'MSc',
                   'EMDOLA', '(Psych)', 'PRYT', 'FHFMA', 'Msc(Statistics)', 'PGCE', 'FCMSA', 'CSCS', 'HTLASCPQHIC',
                   'NPMCN', 'LCPC', 'MSN', 'BGS', 'FACLP FACFE', 'CCRP', 'MAT', 'NCS', 'TTS', 'SCEFS', 'MPS', 'MSW',
                   'PHD', 'l.I.C.S.W', 'BMBS', 'FAARFM', 'DACVM', 'Ed.D.', 'FCSECSA', 'MAMFTC', 'OTA/L', 'CCS', 'WHNP',
                   'ACHCE', 'PHN', 'MMed(Surg)', 'CHIM', 'DMT', 'FACSM', 'LISAC', 'CNM', 'CAPE', 'CBE', 'COBA', 'RHV',
                   'PStat(R)', 'L/CPO', 'MDRS', 'PM', 'REAT', 'CGC', 'NSCA-CSCS', 'MRCOG', 'BPysch', 'honCDWF', 'LT',
                   'CRADC', 'MBB,S', 'CMAC', 'FRCA', 'LPC', ' DVM', 'M.B', 'HT/HTLASCP', 'FCP(SA)', 'CEN', 'ND',
                   'DACVB', 'MC', 'Bch', 'MPAff', 'PHC-NP', 'CEDRDS', 'TSAC-F', 'DC', 'EngDip', 'CHPC', 'CBIS', 'AAMC',
                   'FAAETS', 'ESQ', 'CRC', 'MAN', 'LCCE', 'DMsc', 'LTC', 'CBC', 'M.Med.Sc', 'Pharm D', 'MPh', 'MTR',
                   'FAACT FACLP FACMT FACPsych', 'FRACP', 'MAS', 'CMSR', 'FACN CCD', 'SLPD', 'FAVD', 'Mphil', 'MEng',
                   'FAAPS', 'EMS', 'CTN', 'MMS', 'CLD certified', 'BSC', 'RSW', 'CHW', 'ACM-RN', 'MSE', 'FASE', 'CNSC',
                   'MCR FAPA', 'MASS', 'MBBS, MD (India), FRCPCH, MHPEd, MD (Res)', 'MRes', 'MNAMSFCPE', 'ABFM ABAARM',
                   'McCord', 'OCT', 'AGPCNP-BC', 'FIBP', 'ASW-G', 'QMHA', 'OTD', 'ALB', 'CCNS', 'PHARM.D.',
                   'FFRad(D)(SA)', 'CCC-SLP', 'BVSc', 'FAAFP', 'BCOP', 'MPAS', 'NP', 'MD', 'FACLP FAPA', 'FASGD', 'HSD',
                   'MPharm', 'LGMFT', 'LDN FAND', 'MT', 'FNP-C', 'DFAPA FACLP', 'ATP/SMS', 'PTRP', 'OBE', 'FACDONA',
                   'CASDCS', 'DIP ENDO', 'FACE', 'MRCPsych', 'FWACS', 'APN', 'MHE', 'DPM', 'CISSN', 'CCT', 'MAE',
                   'MClinExPhys', 'OCN', 'CFE', 'PGDip', 'MFA', 'MCHES', 'CDT', 'DNS', 'CHFM',
                   'S Sc (Int Med) (UK) Med.Sc', 'MSBS CCS', 'RRT', 'FANPA FACLP', 'MST', 'MSEd', 'MRCP (UK)',
                   'CLSSMBB', 'ARNP', 'VMD', 'FACC', 'MRCP', 'MAmSA', 'OMS', 'CEDRD-S', 'CSP', 'DScPT', 'BBA', 'FAHA',
                   'MSHCT', 'FCAP', 'MCs', 'MAc', 'CNSs', 'AFN', 'GCNS', 'CNOR', 'SM', 'MSHS', 'DACVS', 'MHS', 'DDSc',
                   'MSHP', 'MSM', 'FANPA', 'Bsc', 'IBCLC', 'FAAOE', 'FRCSEng', 'FRCSC', 'GDip', 'CSEP', 'BDS', 'MSEP',
                   'ACHPN', 'Msc', 'BMedSi(hons)', 'CPHQ', 'FAOCPMR', 'IFASMBS', 'FHM', 'CCHW', 'GCN', 'CHDA', ' CEP',
                   'LBA', 'CURN', 'EMBA', 'DMed Sci', 'CHES', 'AOCN', 'CCD', 'PhDc', 'RCPS', 'CCHFM', 'MSBA', 'CMPP',
                   'CFCS', 'CABIM', 'ET', 'CQIA', 'DDS', 'CHC', 'BScMed(Oxon)', 'FRCSP', 'MPHS', 'FCP', 'HNB-BC',
                   'MHA', 'CVRN', 'MA', 'RDA', 'CCTSI', 'F(ECSA)', 'FCS', 'RHDC', 'DFSVS', 'BS', 'BMedSc',
                   'MD of Science by University of Sao Paulo (USP)', 'FAST', 'MRCP(UK)', 'NCSP', 'BCh', 'DMSci prof',
                   'FCAR', 'FACMQ', 'FRCPI', 'FAMS', 'CHSE', 'MRCGP', 'CCDS', 'RNC-OB', 'MMEL', 'B.E', 'CWT',
                   'F.N.P.-C', 'DO', 'FRCSEdHon', 'DFAPA', 'SNS', 'BHlthMedSc', 'M.B.A.', ' M.Med Sc(Int. Med)',
                   'DABVP', 'MBA,', 'CM CCM', 'CNL', 'III', 'FRCPA', 'CLT', 'MFR', 'LSCW', 'FAED', 'AAS', 'CMAR',
                   'PGCert ClinEd (merit)', 'BAO MRCSI', 'II', 'FAAHB', 'C-MDI', 'RESIDENT', 'BC-ADM', 'BEng', 'MURP',
                   'FACPE', 'ADN', 'CDA', 'LADC ', 'CMD', 'CNP', 'MBChB (honours)', 'VTS', 'Ortho', 'CPEN',
                   'DPhil (Oxon)', 'Dip', 'FRCPC', 'FAES', 'MPTH', 'PsyD', 'CPMHNC', 'FAAN', 'LCSW-C', 'LSSBB',
                   'MSPPM', 'MBBCh', 'DFAPA FACLP FANPA', 'FAAWR', 'FMCS', 'Phd', 'BSci', 'LCMHCS', 'CTRI', 'CHPA',
                   'GNP-BC', 'MHPA', 'CPHI', 'BSc', 'EDD', 'MMEd', 'MPP', 'G Cert Pub Health', 'FMedSci', 'UFCSPA',
                   'Psy', 'DABCC', 'RN-BSN', 'MD (Melb.)', ' ACSM-CEP', 'C.N.P', 'CLC', 'PAASCPCM', 'HSPP', 'MAAT',
                   'CCFC', 'FAAPMR', 'ERYT', 'MBBS (Australia)', 'MMed (UPM)', 'BScMed (Hons)', 'EHS', 'CPI', 'M.Com',
                   'MSHPM', 'FSACME', 'MPE', 'D.C. DCBCN DIBAK CHP', 'AB', 'CCISM', 'Research Alliance (MURAL)', 'DBH',
                   'HSMI', 'CSM', 'ACSM C-EP', 'ACNP-BC', 'AuD', 'NITP', 'MFPHM', 'FACRSI', 'FAAOA', 'BSW', 'FRCPCH',
                   'FMSD', 'MSHI', 'FRCSGlasg', 'CM', 'RCEP FAACVPR', 'FSBI', 'FACG', 'CPO', 'APRN', 'LMFT', 'ECNU',
                   'RMSK', 'RBT', 'BSB', 'F.A.C.S.', 'DLFAPA', 'MNAMEd', 'CSSD', 'FFSc (RCPA)', 'LCAT', 'ACNS-BC',
                   'FARN', 'JD', 'ACUME', 'DSC', 'RPFT', 'ScM', 'CCLS', 'CHCEF', 'P.M.P.', 'AG-ACNP', 'FASCRS', 'MMED',
                   'BA(Cantab)', 'MB, BS (Adel.)', 'CHT', ' CCEP', 'CAS', 'FRCPsych', 'MPsychSc PG DIp CBT', 'PHNA-BC',
                   'APNP', 'LLMSW', 'DM', 'CRS', 'BC-ANCDS', 'MPH', 'CAE', 'L.A.D.C.', 'RTRM', 'FASHE', 'SB', 'CHON',
                   'DMI', 'MCh Thoracic Surgery', 'DSW', 'FT', 'D.O', 'L ADA-C', 'HS', 'FCCP', 'GDPsy', 'MHPE', 'BCPP',
                   'RS', 'LAC', 'CTSS', 'DFASAM', 'ECFMG', 'DFAACAP DFAPA', 'PGCAP', 'DSc', 'MUPD', 'FSVS', 'FCCMG',
                   'GPAC', 'FEBOMF', 'FSSO', 'AM', 'BSIE', 'Medical Student', 'LCAC', 'BC', 'MB', 'EdM', 'CAHIMS',
                   '(A;E) Edin (VCU)', 'Post-CCT', 'DSN', 'FAOASM', 'CCA', 'MLA', 'DESS', 'MBE', 'DFAPA DFAACAP',
                   'MEE FAPA', 'RGN', 'BCACP', 'LRCPI', 'WACP Paediatrics', 'MD(Col)', 'LPN', 'FRCP', 'ACA', 'CDVS',
                   'OHST', 'FACLP FAPA FAACAP FAPOS', 'PMHNP', 'DNP', 'DTMH', 'PFHEA', 'FAIZA', 'FACOEM',
                   'MMed Sc(Int Med)', 'MLS', 'CEDS', 'FRSB', 'PCMH', 'MBe', 'CABM', 'FRCSEd CTh', 'ABOM', 'LDN',
                   'BSEd', 'FRCSUrol', 'AA', 'MSIE', 'CCM', 'DABOM', 'B.A', 'M.D.', 'CPS/A', 'DNSc', 'CS-NS',
                   'DPBP FPPA FPSCAP', 'SFHEA', 'CNML', 'CESP', 'LCMHC', 'FFSc(RCPA)', 'FAOA', 'Pec (SA)', 'MScRes',
                   'F.iaedp', 'DipACLM', 'FFSEM', 'MMT', 'FRCSI', 'EdD', 'P.H', 'DPT', 'MEdPsych', 'AS', 'Hon', 'MPsy',
                   '(India) MHPEd (Res)', 'BSN', 'LIMPH', 'OTR/L', 'C.P.H.', 'CCFT', 'CPWS', 'BCom/BSci',
                   'MD FIBMS CABM MSc Endocrinology', 'CertAVP(EM) DipECEIM MRCVS', 'M.Sc', 'WHNP-BC', 'CNS', 'FAPA',
                   'PEng', 'FCPS', 'CISM', 'LMT', 'CRAADC', 'MCh', 'MFT', 'M.Ed.', '(Epi)', 'DMSc DLFACLP', 'FAAHPM',
                   'CSW', 'FNAP', 'FACEP', 'MS(London)', 'CDE', 'MAPP', 'MS FAACVPR', 'Ms', 'FRANZCR', 'LNCC', 'CNIM',
                   'RYT', 'ASLA', 'FASMBS', 'FEBVS', 'FIDSA', 'FNP', 'LNHA', 'Dr.Med.Sc', 'BHSA', 'ACM-SW', 'MPA',
                   'B Chir', 'MIA', 'ABIM ABoIM AACE', 'DAVDC', 'HB.Sc', 'BM BCH FRCPsych FKC', 'BM', 'MedEd', 'BCB',
                   'MSILS', 'BPsych(Hons)', 'FSGM', 'LD', 'SCS', 'OBS', 'DCH(UK)', 'ABPP', ' MSci', 'FABP', 'FAAOS',
                   'EdS', 'J.D.', 'CFP', 'DACLAM', 'CPP', 'Bus. Hons. CFRM MFINZ', 'DVM', 'EP', 'BSBIO', 'CFRE', 'HPEd',
                   'CSc', 'DNPc', 'ANEF', 'DHSc', 'CMCN', 'DipNB', 'SLP/BCBA', 'LEED-AP', 'DSH', 'PharmD', 'PA-C',
                   'ENDOCRINOLOGY', 'TCRN', 'MPhil', 'MCom', 'PGR Pediatrics', 'CASAC ACSW', 'WACP', 'Pharm.D', 'LADC',
                   'MSCI', 'CCCTM', 'Med.Sc(Endocrinology)', 'MBAn', 'LSSGB', 'DrPH', 'MBBS(UM), MRCP(UK)', ' RCEP',
                   'ATC', 'PNP', 'C-EFM', 'ACSW', 'FESC', 'FRCP(UK)', 'FHIMSS', 'MHCM', 'FEBS', 'CED-S', 'MMBS(Hons)',
                   'ECSA', 'FACLP DFAPA', 'CPH', 'ABN', 'DMSc', 'CMQ', 'MSHA', 'FADCES', 'RNP', 'MBI', 'cPAMs',
                   'pre-BA', 'B.Sc', 'R-MSK', 'CHCA', 'AMFT', 'CTTS', 'BE', 'MPath Chemical Pathology', 'M.R.C.P(UK)',
                   'PD.D.', 'PMP', 'LVT', 'MDiv', 'F-NAP', 'BN', 'MTeach', 'FCPath(Chem)', 'SFHM', 'MB BS', 'DSHS',
                   ' DP M.Ex.Sc', 'DSC h.c. mult', 'MRCPI', 'MMed', 'CT', 'FASCO', 'AIA', 'LAT', 'MDS', 'ScD',
                   'FRCPath', 'FRCS', 'MBBch', 'CCRN', 'CCP', 'LL.M.', 'D.V.M.', 'BMedsi(hons)', 'CASAC CCTP', 'CHb',
                   'CIH', 'FAEDP', 'LHRM', 'FANZCA', 'Speech-Language Pathologist LSLS Cert AVT', 'NCARB', 'FACLP',
                   'M.S.', 'TTW', 'DFACN DFAPA CS', 'DNB', 'ATSF', 'C.H.E.S.', 'DMD', 'PMHCNS', 'MHM',
                   'FACLP DFAACAP DLFAPA', 'CEO', 'RMT', ' LDN', 'DipRCPath', 'FHKAM(Paed)', 'OD', 'BA', 'CPsych',
                   'FAAO', 'RN-CCCTM', 'LISW-CP', 'DEcon', 'FAPWCA', 'FRACS (Gen Surg)', 'CPC', 'LPCC-S', 'FASN', 'LVN',
                   'CC', 'FCS(ECSA)', 'LPA', 'PGCME', 'HTL QIHC', 'CEDS-S', 'BSPH', 'BMedSc (Ire)', 'CCM ACM-SW',
                   'FASA', 'ATR-BC', 'AC-PNP', 'RDMS', 'B.Pharm', 'CADC', 'MBioStat', 'AT', 'NPFA', 'FAAPM', 'CSOWM',
                   'DPhil', 'MBioChem(Hons)', 'FCCM', 'PE', 'MSCR', 'Ph.D.', 'BBMed', 'NCC', 'MMM', 'Au.D.', 'CCE',
                   'LEED AP PQS', 'APHN-BC', 'CCC-SLP/L', 'MBChB', 'DM(endo), DNB(endo)MNAMS', 'CEDRN', 'C-ASWCM',
                   'MAED', 'FISPE', 'CPNP-PC', 'REACE', 'CAADC', 'FID', 'FASHA', 'RVT', 'FRACS', 'MPPM',
                   'FF EMSI K Handler', 'FRCSG', 'MSEE', 'MSCE', 'FWACP', 'ANP', 'MHSci', 'CTRC', 'CPHIMS', 'MWACS',
                   'CCHP', 'MFPH', 'PT', 'PGDHP', 'Consultant Endocrinologist (Col) (UK)', 'SBIM', 'RD', 'ChB',
                   'FAcadTM', 'ATP', 'CSE', 'C-IAYT', 'FRCSEd', 'FSAHM', 'DLFAPA FACLP', 'BS EP', 'CSSM', 'MSUP',
                   'NE-BC', 'DHS', ' MMM', 'MIFSM', 'CSSBB', 'HTASCP', 'FACLP DLFAPA', 'MABS',
                   'M.Med (Int.Medicine) (UK)', 'CPHRM', 'AE-C', 'PGDipCH', 'FNSCA', 'MEng.', 'FAPCR',
                   '(honours) PGCert ClinEd (merit)', 'BCD', 'DABFM', 'LEED AP', 'NR-P', 'LGSW', 'CTR', 'LCMHC NCC',
                   'LMSSW', 'F-ASHA', 'MEHP', 'FHEA', 'ACPR', 'RDH', 'MPPA', 'MPT', 'BTech', 'BMed', 'BEc', 'FDS',
                   'CRA', 'CCRC', 'Esq', 'ESA', 'RTP', 'N.P', 'CRRN', 'FGSA', 'M.S', 'ASN', 'MME', 'FMAS', 'FIISE',
                   '(Diab;Endo)', 'PCS', 'PHARMD', 'MBBS, MRCP(UK), FRCP (Edin)', 'MSTR', 'CPNP', 'FSVM', 'LCSW',
                   'CEDRD', 'DScHon', 'MSHSE', 'FHKAN', 'FASAM', 'MAppSpSci', 'MBchB', 'CARC', 'DipMedEd', 'BCBA',
                   'RNFA', 'DWC', 'Dr.Ph', 'phd', 'MAATC', 'RCPT', 'MEd', 'CIV', 'FISMRM', 'ESBQ', 'CEM', 'MSC',
                   'BMedSc (Ire) (UPM)', 'MSPH', 'FPSEDM', 'DTM&H', 'FACLP FAPA FATA', 'MBBChir', 'SCD', 'LMSW', 'FAUR',
                   'MHP', 'D.Phil', 'BCMAS', 'FAFRMRACP', 'ASA', 'CCTP', 'Pharm.M', 'M.D', 'R.N', 'BSc(Hons)', 'CHB',
                   'FEAS', 'NLPT', 'RN', 'FAACVPR', 'Hons', 'MSP', 'M.P.P.', 'CEEAA', 'MRCPUK', 'RDCS', 'FASHP',
                   'BBiomedSc(Hons)', 'CENP', 'APR', 'ASCP', 'AGPCNP', 'FAPA FACLP', 'BExSpSci', 'NADD-DDS',
                   ' MSPT BHMS', 'FHKAM (Paed)', '(med)', 'FACRS', 'EFIAGES', 'LICSW', 'CPT', 'FIBMS Endocrinology',
                   'RHIA', 'MS', 'DMin', 'OTR', 'MCS', 'Mpm', 'BScN', 'CBSP', 'CCDP-D', 'MI', 'MOT', 'HHCNS-BC', 'MAM',
                   'FFPMANZCA', 'CNE', 'CCWH', 'MSMS', 'PCCN', 'FAAMA', 'LSW', '(GENERAL MEDICINE)', 'AOCNP',
                   'HTLASCPCM', 'FMCPath', 'FMCR', 'B. Pharm', 'LLB', ' Dipl. Lac', 'DAc.', 'FRCPath', 'MBChB', 'FRCPC',
                   'M.Phil.', 'MSW', 'MFT', ' LCMFT']
    for x in sorted(degree_list, key=len, reverse=True):
        name = name.replace(f', {x}', f'# {x}')
    return name



if __name__ == '__main__':
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
    }
    JOURNAL_NAME = os.path.basename(__file__).rstrip('.py')
    BASE_URL = ''
    src_url = 'https://changing-sp.com/ojs/index.php/csp/issue/archive'
    journal_name = 'Changing Societies and Personalities'
    journal_url = src_url
    issn_number = '2587-6104; 2587-8964'
    page_nav = src_url
    '''while loop using for page navigation'''
    while page_nav is not None:
        try:
            page_link = page_nav['href']
        except:
            page_link = page_nav
        page_soup = get_soup(page_link, headers)
        issue_content = page_soup.find_all('a', class_='title')
        for single_issue in issue_content:
            issue_url = single_issue['href']
            issue_soup = get_soup(issue_url, headers)
            inner_content = issue_soup.find_all('div', class_='title')
            for single_article in inner_content:
                article_url = single_article.a['href']
                print(article_url)
                if article_url in read_log_file():
                    continue
                article_soup = get_soup(article_url, headers)
                if article_soup is None:
                    continue
                '''ARTICLE CONTENT'''
                article_content = article_soup.find('article', class_='obj_article_details')
                '''ABSTRACT TITLE'''
                try:
                    title_tag = article_content.find('h1', class_='page_title')
                    abstract_title = abstract_cleaner(title_tag)
                except:
                    abstract_title = ''
                '''AUTHOR AND AFFILIATION'''
                try:
                    aut_aff = article_content.find('ul', class_='authors').find_all('li')
                    author_list = []
                    affiliation_list = []
                    seq = 1
                    for single_aut_aff in aut_aff:
                        authors = single_aut_aff.find('span', class_='name').text.strip()
                        if single_aut_aff.find('span', class_='affiliation'):
                            aff = single_aut_aff.find('span', class_='affiliation').text.strip()
                            if ';' in str(aff):
                                aff_split = aff.split(';')
                                author_seq_list = []
                                for single_aff in aff_split:
                                    aff_strip = single_aff.strip()
                                    affiliation_list.append(f'{seq} {aff_strip}')
                                    author_seq_list.append(str(seq))
                                    seq += 1
                                author_list.append(authors + ', '.join(author_seq_list))
                            else:
                                author_list.append(f'{authors} {seq}')
                                affiliation_list.append(f'{seq} {aff}')
                                seq += 1
                        else:
                            author_list.append(f'{authors} {0}')
                    author_join = '; '.join(author_list)
                    affiliation_join = '; '.join(affiliation_list)
                except:
                    author_join = ''
                    affiliation_join = ''
                '''DOI'''
                try:
                    if article_content.find('div', class_='item doi'):
                        doi = article_content.find('div', class_='item doi').a['href']
                    elif article_content.find('section', class_='item doi'):
                        doi = article_content.find('section', class_='item doi').a['href']
                    else:
                        doi = ''
                except:
                    doi = ''
                '''KEYWORDS'''
                try:
                    if article_content.find('div', class_='item keywords'):
                        keyword = article_content.find('div', class_='item keywords').find('span', class_='value')
                        keywords = abstract_cleaner(keyword)
                    elif article_content.find('section', class_='item keywords'):
                        keyword = article_content.find('section', class_='item keywords').find('span', class_='value')
                        keywords = abstract_cleaner(keyword)
                    else:
                        keywords = ''
                except:
                    keywords = ''
                '''ABSTRACT BLOCK'''
                try:
                    if article_content.find('div', class_='item abstract'):
                        abstract_block = article_content.find('div', class_='item abstract')
                        abstract_join = abstract_cleaner(abstract_block).replace('Abstract', '').strip()
                    elif article_content.find('section', class_='item abstract'):
                        abstract_block = article_content.find('section', class_='item abstract')
                        abstract_join = abstract_cleaner(abstract_block).replace('Abstract', '').strip()
                    else:
                        abstract_join = ''
                except:
                    abstract_join = ''
                '''FULL TEXT URL'''
                try:
                    full_text_url = article_content.find('a', class_='obj_galley_link pdf')['href']
                except:
                    full_text_url = ''
                '''VOLUME AND ISSUE'''
                try:
                    vol_issue = article_content.find('div', class_='item issue').find('a',
                                                                                      class_='title').text.strip()
                    content_split = vol_issue.split('(', 1)
                    vol_tag = content_split[0].strip()
                    year_data = content_split[-1].split(')', 1)[0].strip()
                    if 'No.' in str(vol_tag):
                        volume = vol_tag.split('No.', 1)[0].replace('Vol.', '').strip()
                        issue = vol_tag.split('No.', 1)[-1].strip()

                    else:
                        volume = vol_tag.replace('Vol.', '').strip()
                        issue = ''
                    year_tag = re.search('(\d{4})', str(year_data)).group()
                except:
                    year_tag = ''
                    volume = ''
                    issue = ''
                '''PUBLISH DATE'''
                try:
                    date = article_content.find('div', class_='item published').find('div',
                                                                                     class_='value').text.strip()
                    publish_date = strip_it(date)
                    year = re.search('(\d{4})', str(publish_date)).group()
                except:
                    year = year_tag.strip()
                    publish_date = f'01/01/{year}'
                '''REFERENCE'''
                try:
                    if article_content.find('div', class_='item references'):
                        ref = article_content.find('div', class_='item references')
                        if ref.find('p'):
                            ref_list = []
                            for single_ref in ref.find_all('p'):
                                ref_text = abstract_cleaner(single_ref)
                                ref_list.append(ref_text)
                            reference = ' '.join(ref_list)
                        else:
                            reference = abstract_cleaner(ref)
                    elif article_content.find('section', class_='item references'):
                        ref = article_content.find('section', class_='item references')
                        if ref.find('p'):
                            ref_list = []
                            for single_ref in ref.find_all('p'):
                                ref_text = abstract_cleaner(single_ref)
                                ref_list.append(ref_text)
                            reference = ' '.join(ref_list)
                        else:
                            reference = abstract_cleaner(ref)
                    else:
                        reference = ''
                except:
                    reference = ''
                print('current datetime------>', datetime.now())
                dictionary = {
                    "journalname": journal_name,
                    "journalabbreviation": "",
                    "journalurl": journal_url,
                    "year": year,
                    "issn": issn_number,
                    "volume": volume,
                    "issue": issue,
                    "articletitle": strip_it(abstract_title),
                    "doiurl": doi,
                    "author": strip_it(author_join),
                    "author_affiliation": strip_it(affiliation_join),
                    "abstractbody": strip_it(abstract_join),
                    "keywords": strip_it(keywords),
                    "fulltext": '',
                    "fulltexturl": full_text_url,
                    "publisheddate": publish_date,
                    "conflictofinterests": "",
                    "otherurl": '',
                    "articleurl": article_url,
                    "pubmedid": "",
                    "pmcid": "",
                    "sponsors": '',
                    "manualid": "",
                    "country": "",
                    "chemicalcode": "",
                    "meshdescriptioncode": "",
                    "meshqualifiercode": "",
                    "medlinepgn": "",
                    "language": "",
                    "nlmuniqueid": "",
                    "datecompleted": "",
                    "daterevised": '',
                    "medlinedate": "",
                    "studytype": "",
                    "isboolean": "",
                    "nativetitle": '',
                    "nativeabstract": '',
                    "citations": "",
                    "reference": reference,
                    "disclosure": "",
                    "acknowledgements": '',
                    "supplement_url": ""
                }
                articles_df = pd.DataFrame([dictionary])
                if os.path.isfile(f'{JOURNAL_NAME}.csv'):
                    articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False, header=False,
                                       mode='a')
                else:
                    articles_df.to_csv(f'{JOURNAL_NAME}.csv', index=False)
                write_visited_log(article_url)
        page_data = page_soup.find('div', class_='cmp_pagination').find('strong')
        page_nav = page_data.find_next_sibling('a')