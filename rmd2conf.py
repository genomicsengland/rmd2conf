#!/usr/bin/python
#
# --------------------------------------------------------------------------------------------------------
# Thompson Rmarkdown to Confluence Tool
# --------------------------------------------------------------------------------------------------------
# Create or Update Confluence pages remotely using markdown or Rmarkdown files.
#
# --------------------------------------------------------------------------------------------------------
# Usage: rmd2conf.py markdown-or-rmarkdown-file -u <confluence-user-name> -p <confluence-password>
# --------------------------------------------------------------------------------------------------------

import  sys, os, shutil, subprocess
import  markdown, mimetypes, codecs
import  re, collections
import  requests, json
import  argparse, urllib.parse, webbrowser
import  datetime

# ArgumentParser to parse arguments and options
parser = argparse.ArgumentParser()
parser.add_argument("inputFile", help="Full path of the Rmarkdown or markdown file to convert and upload.")
parser.add_argument('-s', '--spacekey', default='CDT', help="Confluence Space key for the page. If omitted, will use CDT space.")
parser.add_argument('-u', '--username', help='Confluence username.')
parser.add_argument('-p', '--password', help='Confluence password.')
parser.add_argument('-t', '--pagetitle', help='Page title.')
parser.add_argument('-a', '--ancestor', help='Parent page under which page will be created or moved.')
parser.add_argument('-m', '--attachment', nargs='+', help='Attachment(s) to upload to page. Paths relative to the markdown file.')
parser.add_argument('-c', '--contents', action='store_true', default=False, help='Use this option to generate a contents page.')
parser.add_argument('-g', '--nogo', action='store_true', default=False, help='Use this option to skip navigation after upload.')
parser.add_argument('-n', '--nossl', action='store_true', default=False, help='Use this option if NOT using SSL. Will use HTTP instead of HTTPS.')
parser.add_argument('-d', '--delete', action='store_true', default=False, help='Use this option to delete the page instead of create it.')
parser.add_argument('-b', '--makebackup', action='store_true', default=False, help='Use this option to keep the generated markdown from Rmd file')
args = parser.parse_args()

# Assign global variables
try:
    inputFile = args.inputFile
    fileext = os.path.splitext(inputFile)[1]
    spacekey = args.spacekey
    username = args.username
    password = args.password
    pagetitle = args.pagetitle
    ancestor = args.ancestor
    nossl = args.nossl
    delete = args.delete
    attachments = args.attachment
    goToPage = not args.nogo
    contents = args.contents
    keepmd= args.makebackup
    wikiUrl = "https://cnfl.extge.co.uk"
       
    if inputFile is None:
        print('Error: markdown file not specified')

    if username is None:
        print('Error: Username not specified.')
        sys.exit(1)
               
    if password is None:
        print('Error: Password not specified.')
        sys.exit(1)
               
    if not os.path.exists(inputFile):
        print('Error: markdown file: %s does not exist.' % (inputFile))
        sys.exit(1)

    if fileext.upper() not in ['.RMD', '.MD']:
        print('Error: %s not recognised format' & (inputFile))
       
    if nossl:
        wikiUrl.replace('https://','http://')
                        
except Exception as err:
    print('Exception caught:\n%s ' % (err))
    print('Failed to process command line arguments. Exiting.')
    sys.exit(1)

#to convert Rmd file to md file, first delete any previous md document that might have been generated
def convertRmdToMd(markdownFile):
    print('Converting Rmarkdown file %s' % markdownFile)
    n = os.path.splitext(markdownFile)[0] + '{:%Y-%m-%d-%H%M%S}'.format(datetime.datetime.now()) + '.md'
    cmd = "rmarkdown::render(\'" + markdownFile + "\', output_format = \'md_document\', output_file = \'" + os.path.basename(n) + "\')"
    try:
        subprocess.check_output(["R", "-e", cmd])
        return n
    except Exception as err:
        print('Failed to convert Rmarkdown file' + err)
        sys.exit(1)

#to delete converted markdown file and it's files
def delConvertedMd(md):
	d = os.path.splitext(md)[0] + '_files'
	if os.path.isdir(d):
		shutil.rmtree(d)
	os.remove(md)

# Convert html code blocks to Confluence macros
def convertCodeBlock(html):
    codeBlocks = re.findall('<pre><code.*?>.*?<\/code><\/pre>', html, re.DOTALL)
    if codeBlocks:
        for tag in codeBlocks:
                        
            confML = '<ac:structured-macro ac:name="code">'
            confML = confML + '<ac:parameter ac:name="theme">Default</ac:parameter>'
            confML = confML + '<ac:parameter ac:name="linenumbers">false</ac:parameter>'
                        
            lang = re.search('code class="(.*)"', tag)
            if lang:
                lang = lang.group(1)
            else:
                lang = 'none'
                                
            confML = confML + '<ac:parameter ac:name="language">' + lang + '</ac:parameter>'
            content = re.search('<pre><code.*?>(.*?)<\/code><\/pre>', tag, re.DOTALL).group(1)
            content = '<ac:plain-text-body><![CDATA[' + content + ']]></ac:plain-text-body>'
            confML = confML + content + '</ac:structured-macro>'
            confML = confML.replace('&lt;', '<').replace('&gt;', '>')
            confML = confML.replace('&quot;', '"').replace('&amp;', '&')
                        
            html = html.replace(tag, confML)
        
    return html

# Converts html for info, note or warning macros
def convertInfoMacros(html):
        
    infoTag = '<p><ac:structured-macro ac:name="info"><ac:rich-text-body><p>'
    noteTag = infoTag.replace('info','note')
    warningTag = infoTag.replace('info','warning')
    closeTag = '</p></ac:rich-text-body></ac:structured-macro></p>'
        
    # Custom tags converted into macros
    html=html.replace('<p>~?', infoTag).replace('?~</p>', closeTag)
    html=html.replace('<p>~!', noteTag).replace('!~</p>', closeTag)
    html=html.replace('<p>~%', warningTag).replace('%~</p>', closeTag)
                
    # Convert block quotes into macros
    quotes = re.findall('<blockquote>(.*?)</blockquote>', html, re.DOTALL)
    if quotes:
        for q in quotes:
            note = re.search('^<.*>Note', q.strip(), re.IGNORECASE)
            warning = re.search('^<.*>Warning', q.strip(), re.IGNORECASE)
                                
            if note:
                cleanTag = stripType(q, 'Note')
                macroTag = cleanTag.replace('<p>', noteTag).replace('</p>', closeTag).strip()
            elif warning:
                cleanTag = stripType(q, 'Warning')
                macroTag = cleanTag.replace('<p>', warningTag).replace('</p>', closeTag).strip()
            else:
                macroTag = q.replace('<p>', infoTag).replace('</p>', closeTag).strip()
                        
            html = html.replace('<blockquote>%s</blockquote>' % q, macroTag)
    return html
        
# Strips Note or Warning tags from html in various formats
def stripType(tag, type):
    tag = re.sub('%s:\s' % type, '', tag.strip(), re.IGNORECASE)
    tag = re.sub('%s\s:\s' % type, '', tag.strip(), re.IGNORECASE)
    tag = re.sub('<.*?>%s:\s<.*?>' % type, '', tag, re.IGNORECASE)
    tag = re.sub('<.*?>%s\s:\s<.*?>' % type, '', tag, re.IGNORECASE)
    tag = re.sub('<(em|strong)>%s:<.*?>\s' % type, '', tag, re.IGNORECASE)
    tag = re.sub('<(em|strong)>%s\s:<.*?>\s' % type, '', tag, re.IGNORECASE)
    tag = re.sub('<(em|strong)>%s<.*?>:\s' % type, '', tag, re.IGNORECASE)
    tag = re.sub('<(em|strong)>%s\s<.*?>:\s' % type, '', tag, re.IGNORECASE)
    stringStart = re.search('<.*?>', tag)
    tag = upperChars(tag, [stringStart.end()])
    return tag
        
# Make characters uppercase in string
def upperChars(string, indices):
    upperString = "".join(c.upper() if i in indices else c for i, c in enumerate(string))
    return upperString

# Process references
def processRefs(html):
    refs = re.findall('\n(\[\^(\d)\].*)|<p>(\[\^(\d)\].*)', html)
        
    if len(refs) > 0:
                        
        for ref in refs:
            if ref[0]:
                fullRef = ref[0].replace('</p>', '').replace('<p>', '')
                refID = ref[1]
            else:
                fullRef = ref[2]
                refID = ref[3]
                
            fullRef = fullRef.replace('</p>', '').replace('<p>', '')
            html = html.replace(fullRef, '')
            href = re.search('href="(.*?)"', fullRef).group(1)
            
            superscript = '<a id="test" href="%s"><sup>%s</sup></a>' % (href, refID)
            html = html.replace('[^%s]' % refID, superscript)
        
    return html

# Retrieve page details by title
def getPage(title):
    print('\tRetrieving page information: %s' % title)
    url = '%s/rest/api/content?title=%s&spaceKey=%s&expand=version,ancestors' % (wikiUrl, urllib.parse.quote_plus(title), spacekey)

    s = requests.Session()
    s.auth = (username, password)
        
    r = s.get(url)
        
        # Check for errors
    try:
        r.raise_for_status()
    except Exception as err:
        error = re.search('^404', err.message)
        if error:
            print('\nError: Page not found. Check the following are correct:')
            print('\tSpace Key : %s' % spacekey)
        sys.exit(1)
                
    data = r.json()
        
    if len(data[u'results']) >= 1:
        pageId = data[u'results'][0][u'id']
        versionNum =  data[u'results'][0][u'version'][u'number']
        link = '%s%s' % (wikiUrl, data[u'results'][0][u'_links'][u'webui'])
                
        pageInfo = collections.namedtuple('PageInfo', ['id','version', 'link'])
        p = pageInfo(pageId, versionNum, link)
        return p
    else:
        return False

# Scan for images and upload as attachments if found
def addImages(pageId, html):
    #sourceFolder = os.path.dirname(os.path.abspath(inputFile)).decode('utf-8')
    sourceFolder = os.path.dirname(os.path.abspath(inputFile))
        
    for tag in re.findall('<img(.*?)\/>', html):
        relPath = re.search('src="(.*?)"', tag).group(1)
        altText = re.search('alt="(.*?)"', tag).group(1)
        absPath = os.path.join(sourceFolder, relPath)
        basename = os.path.basename(relPath)
        uploadAttachment(pageId, absPath, altText)
        if re.search('http.*', relPath) is None:
            html = html.replace('%s'%(relPath),'/download/attachments/%s/%s'%(pageId, basename))
        
    return html

# Add contents page
def addContents(html):
    contentsMarkup = '<ac:structured-macro ac:name="toc">\n<ac:parameter ac:name="printable">true</ac:parameter>\n<ac:parameter ac:name="style">disc</ac:parameter>'
    contentsMarkup = contentsMarkup + '<ac:parameter ac:name="maxLevel">5</ac:parameter>\n<ac:parameter ac:name="minLevel">1</ac:parameter>'
    contentsMarkup = contentsMarkup + '<ac:parameter ac:name="class">rm-contents</ac:parameter>\n<ac:parameter ac:name="exclude"></ac:parameter>\n<ac:parameter ac:name="type">list</ac:parameter>'
    contentsMarkup = contentsMarkup + '<ac:parameter ac:name="outline">false</ac:parameter>\n<ac:parameter ac:name="include"></ac:parameter>\n</ac:structured-macro>'
        
        
    html = contentsMarkup + '\n' + html
    return html

# Add attachments for an array of files
def addAttachments(pageId, files):
    #sourceFolder = os.path.dirname(os.path.abspath(inputFile)).decode('utf-8')
    sourceFolder = os.path.dirname(os.path.abspath(inputFile))
        
    if files:
        for file in files:
            uploadAttachment(pageId, os.path.join(sourceFolder, file), '')
        
# Create a new page
def createPage(title, body, ancestors):
    print('\nCreating page...')
        
    url = '%s/rest/api/content/' % wikiUrl
        
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'Content-Type' : 'application/json'})
        
    newPage = { 'type' : 'page', \
         'title' : title, \
         'space' : {'key' : spacekey}, \
         'body' : { \
                'storage' : { \
                        'value' : body, \
                        'representation' : 'storage' \
                        } \
                }, \
         'ancestors' : ancestors \
         }
        
    r = s.post(url, data=json.dumps(newPage))
    r.raise_for_status()
        
    if r.status_code == 200:
        data = r.json()
        spaceName = data[u'space'][u'name']
        pageId = data[u'id']
        version = data[u'version'][u'number']
        link = '%s%s' %(wikiUrl, data[u'_links'][u'webui'])
                
        print('\nPage created in %s with ID: %s.' % (spaceName, pageId))
        print('URL: %s' % link)
                
        imgCheck = re.search('<img(.*?)\/>', body)
        if imgCheck or attachments:
            print('\tAttachments found, update procedure called.')
            updatePage(pageId, title, body, version, ancestors, attachments)
        else:
            if goToPage:
                webbrowser.open(link)
    else:
        print('\nCould not create page.')
        sys.exit(1)

# Delete a page
def deletePage(pageId):
    print('\nDeleting page...')
    url = '%s/rest/api/content/%s' % (wikiUrl, pageId)
        
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'Content-Type' : 'application/json'})

    r = s.delete(url)
    r.raise_for_status()
        
    if r.status_code == 204:
        print('Page %s deleted successfully.' % pageId)
    else:
        print('Page %s could not be deleted.' % pageId)

# Update a page
def updatePage(pageId, title, body, version, ancestors, attachments):
    print('\nUpdating page...')
        
    # Add images and attachments
    body = addImages(pageId, body)
    addAttachments(pageId, attachments)
    
    url = '%s/rest/api/content/%s' % (wikiUrl, pageId)
        
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'Content-Type' : 'application/json'})
        
    pageJson = { \
                "id" : pageId, \
                "type" : "page", \
                "title" : title, \
                "space" : { "key": spacekey }, \
                "body" : { \
                "storage": { \
                        "value": body, \
                        "representation": "storage" \
                         } \
                }, \
                "version" : { \
                        "number" : version+1 \
                }, \
                'ancestors' : ancestors \
    }
        
    r = s.put(url, data=json.dumps(pageJson))
    r.raise_for_status()
        
    if r.status_code == 200:
        data = r.json()
        link = '%s%s' %(wikiUrl, data[u'_links'][u'webui'])
                
        print('\nPage updated successfully.')
        print('URL: %s' % link)
        if goToPage:
            webbrowser.open(link)
    else:
        print("\nPage could not be updated.")

def getAttachment(pageId, filename):
    url = '%s/rest/api/content/%s/child/attachment?filename=%s' % (wikiUrl, pageId, filename)
        
    s = requests.Session()
    s.auth = (username, password)
        
    r = s.get(url)
    r.raise_for_status()
    data = r.json()
        
    if len(data[u'results']) >= 1:
        attId = data[u'results'][0]['id']       
        attInfo = collections.namedtuple('AttachmentInfo', ['id'])
        a = attInfo(attId)
        return a
    else:
        return False

# Upload an attachment  
def uploadAttachment(pageId, file, comment):
        
    if re.search('http.*', file):
        return False
        
    contentType = mimetypes.guess_type(file)[0]
    fileName = os.path.basename(file)
    
    fileToUpload = {
            'comment' : comment,
            'file' : (fileName, open(file, 'rb'), contentType, {'Expires': '0'})
    }
        
    attachment = getAttachment(pageId, fileName)
    if attachment:
        url = '%s/rest/api/content/%s/child/attachment/%s/data' % (wikiUrl, pageId, attachment.id)
    else:
        url = '%s/rest/api/content/%s/child/attachment/' % (wikiUrl, pageId)
        
    s = requests.Session()
    s.auth = (username, password)
    s.headers.update({'X-Atlassian-Token' : 'no-check'})
        
    print('\tUploading attachment %s...' % fileName)
        
    r = s.post(url, files=fileToUpload)
    r.raise_for_status()
        

def main():
    try:
        if fileext.upper() == '.RMD':
            markdownFile = convertRmdToMd(inputFile)
        else:
            markdownFile = inputFile
        with open(markdownFile, 'r') as f:
            if pagetitle is None:
                title = f.readline().strip()
            else:
                title = pagetitle
            f.seek(0)
            mdContent = f.read()
    except Exception as err:
        print('Error accessing md/rmd file:' + err)
        sys.exit(1)
                
    print('Title:\t\t%s' % title)
        
    with codecs.open(markdownFile,'r','utf-8') as f:
        html=markdown.markdown(f.read(), extensions = ['markdown.extensions.tables', 'markdown.extensions.fenced_code'])
        
    html = '\n'.join(html.split('\n')[1:])
        
    html = convertInfoMacros(html)
    html = convertCodeBlock(html)
        
    if contents:
        html = addContents(html)

    html = processRefs(html)

    print('Checking if Atlas page exists...')
    page = getPage(title)
        
    if delete and page:
        deletePage(page.id)
        sys.exit(1)
                
    if ancestor:
        parentPage = getPage(ancestor)
        if parentPage:
            ancestors = [{'type':'page','id':parentPage.id}]
        else:
            print('Error: Parent page does not exist: %s' % ancestor)
            sys.exit(1)
    else:
        ancestors = []
        
    if page:
        updatePage(page.id, title, html, page.version, ancestors, attachments)
    else:
        createPage(title, html, ancestors)
        
    if keepmd is False and fileext.upper() == '.RMD':
        delConvertedMd(markdownFile)

    print('Markdown Converter completed successfully.')

if __name__ == "__main__":
    main()
