#!/usr/bin/python
#
# python script to deploy to CDN
#
import base64
import boto
import ConfigParser
import hashlib
import optparse
import os
import sys

#BOTO_VERSION = '2.0b3'
#BOTO_VERSION = '1.9b'

def calc_md5(afile, blocksize=65536):
	hasher = hashlib.md5()
	buf = afile.read(blocksize)
	while len(buf) > 0:
		hasher.update(buf)
		buf = afile.read(blocksize)
	return hasher.digest()

parser = optparse.OptionParser()
parser.add_option("--bucket", dest="bucket_name", help="bucket (default=key.fileformat.info)", default="key.fileformat.info")
parser.add_option("--check-existing", action="store_true", dest="checkExisting", help="checking existing files", default=False)
parser.add_option("--nocache", action="store_false", dest="cache", help="do not set cache headers (default=set)", default=True)
parser.add_option("--output", dest="destpath", help="destination path on CDN (default=/)", default="/")
parser.add_option("--input", dest="srcpath", help="source path on local filesystem (default=./www)", default="./www")
parser.add_option("--update", action="store_true", dest="ifUpdate", help="do the actual copy (otherwise just a dry run)", default=False)
parser.add_option("--verbose", action="store_true", dest="verbose", help="verbose status messages", default=False)

(options, args) = parser.parse_args()

#if boto.Version != BOTO_VERSION:
	#print("ERROR: boto must be version %s (actual is %s)" % (BOTO_VERSION, boto.Version))
	#sys.exit(1)

#
# input should have trailing slash
#
if options.srcpath[-1:] != '/':
	options.srcpath = options.srcpath + '/'

#
# output should *not* have a leading slash
#
if len(options.destpath) > 0 and options.destpath[0:1] == '/':
	options.destpath = options.destpath[1:]

print("INFO: copying from '%s' to '%s' on '%s'" % (options.srcpath, options.destpath, options.bucket_name))

metadata = dict( {
	'.gif': [ ('Content-Type', 'image/gif') ],
	'.html':[ ('Content-Type', 'text/html; charset=UTF-8') ],
	'.ico': [ ('Content-Type', 'image/x-icon') ],
	'.jpeg': [ ('Content-Type', 'image/jpeg') ],
	'.jpg': [ ('Content-Type', 'image/jpeg') ],
	'.json':[ ('Content-Type', 'application/x-javascript; charset=UTF-8') ],
	'.m4a': [ ('Content-Type', 'audio/mp4') ],
	'.pdf': [ ('Content-Type', 'application/pdf') ],
	'.png': [ ('Content-Type', 'image/png') ],
	'.properties': [ ('Content-Type', 'text/plain; charset=UTF-8') ],
	'.rdf': [ ('Content-Type', 'application/rdf+xml') ],
	'.svg': [ ('Content-Type', 'image/svg+xml') ],
	'.swf': [ ('Content-Type', 'application/x-shockwave-flash') ],
	'.tiff': [ ('Content-Type', 'image/tiff') ],
	'.txt': [ ('Content-Type', 'text/plain; charset=UTF-8') ],
	'.xml': [ ('Content-Type', 'text/xml; charset=UTF-8') ],
	'.xpi': [ ('Content-Type', 'application/x-xpinstall') ],
	} )


# to just check the content without making changes:
if options.ifUpdate == False:
	print("INFO: dry-run!  no files will be copied")

config = ConfigParser.RawConfigParser()
config.read('/etc/fileformatnet/rosetta-key.ini')

if config.has_option('credentials', 'access_key_id') == False:
	print("ERROR: Invalid account: No id")
	sys.exit(1)

if config.has_option('credentials', 'secret_access_key') == False:
	print("ERROR: Invalid account: No secret")
	sys.exit(2)

provider_key = config.get('credentials', 'access_key_id')
provider_secret = config.get('credentials', 'secret_access_key')

conn = boto.connect_s3(provider_key, provider_secret)

bucket = conn.get_bucket(options.bucket_name)

existing = {}

if options.checkExisting:
	print("INFO: loading existing file info")
	keys = bucket.list(options.destpath)
	for key in keys:
		existing[key.key] = key

	print("INFO: %d existing files" % (len(existing)))

skipCount = 0
uploadCount = 0

for root, dirs, files in os.walk(options.srcpath):

	for filename in files:

		(shortname, extension) = os.path.splitext(filename)

		fullpath = os.path.join(root, filename)
		deploypath = os.path.join(options.destpath, fullpath[len(options.srcpath):])
		if options.verbose:
			print("INFO: processing %s %s" % (fullpath, deploypath))

		fp = open(fullpath, 'rb')
		md5sum_binary = calc_md5(fp)
		fp.close()
		md5sum = ''.join( [ "%02x" % ord( x ) for x in md5sum_binary ] )
		md5sum_base64 = base64.b64encode(md5sum_binary)
		print("INFO: md5sum is %s (%s)" % (md5sum, md5sum_base64))

		if deploypath in existing:
			current = existing.pop(deploypath)
			# LATER: switch to content-md5 header when S3 supports it
			if '"' + md5sum + '"' == current.etag:
				print("INFO: skipping %s: md5sum unchanged (%s vs %s)" % (deploypath, md5sum, current.etag))
				skipCount += 1
				continue

		print("INFO: uploading %s" % deploypath)
		uploadCount += 1
		if options.ifUpdate:
			s3obj = boto.s3.key.Key(bucket)
			s3obj.key = deploypath
			s3obj.set_metadata('Content-MD5', md5sum_base64)
			if options.cache:
				s3obj.set_metadata('Cache-Control', 'max-age=31536000')
				s3obj.set_metadata('Expires', 'Thu, 31 Dec 2037 23:59:59 GMT')

			if extension not in metadata:
				print("WARNING: no metadata for '%s'" % (extension))
			else:
				extra_meta_list = metadata[extension]
				for extra_meta in extra_meta_list:
					s3obj.set_metadata(extra_meta[0], extra_meta[1])

			s3obj.set_contents_from_filename(fullpath)
			#s3obj.make_public()

if options.checkExisting:
	if len(existing) > 0:
		print("WARNING: %d files deployed but not present locally:" % len(existing))
		keys = existing.keys()
		keys.sort()
		for key in keys:
			print("WARNING: file %s not found locally" % key)

if options.ifUpdate == False:
	print("INFO: dry-run!  no files copied")

print("INFO: complete (%d uploads, %d existing)" % (uploadCount, skipCount))

