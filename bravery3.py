# -*- coding: utf-8 -*-
import time
import praw
import random
import string
import re
from collections import deque
import sys
import os
from ConfigParser import SafeConfigParser

config = SafeConfigParser()
config.read('bravery.conf')

USERNAME = config.get('AccountInfo', 'username')
USERNAME2 = config.get('AccountInfo', 'username2')
PASSWORD = config.get('AccountInfo', 'password')

######################################################################
####################### BEGIN BRAVERY RULES. #########################

#Will import all rules from /rules
ruledir = os.listdir('./rules')
for item in ruledir:
    if item[-3:] == '.py':    #determines if file is a python script
        try:
            execfile('./rules/'+item)    #executes all the code in the file
        except Exception, ex:    #if error in the code, say so
            print 'There was an error when parsing rule file '+item
            print 'Try debugging the file and try again.'
######################## END BRAVERY RULES. ##########################
######################################################################






######################################################################
##################### BEGIN CONFIGURATION LISTS ######################

#imports comment rule list from config
listOfCommentRules = {}
for rule in config.get('Rules', 'CommentRules').strip().split(","):
    try:
        listOfCommentRules[eval(rule)] = rule
    except NameError:
        print 'Error when loading comment rule \''+rule+'\'. Check if the containing rule file was parsed sucessfully'

#imports submission rule list from config
listOfSubmissionRules = {}
for rule in config.get('Rules', 'SumissionRules').strip().split(","):
    try:
        listOfSubmissionRules[eval(rule)] = rule
    except NameError:
        print 'Error when loading submission rule \''+rule+'\'. Check if the containing rule file was parsed sucessfully'

# List of subreddits to check all rules in.
trackingSubreddits = config.get('Subreddits', 'TrackingSubreddits').strip().split(",")

#Will be managed by r2 instead:
bannedSubreddits = config.get('Subredddits', 'BannedSubreddits').strip().split(",")

# These subreddits will not be checked by any rules EXCEPT those which explicitly
# say so in subredditRestrictions.
specialSubreddits = config.get('Subreddits', 'SpecialSubreddits').strip().split(",")

# Every rule listed here will be applied only to comments or submissions in the
# subreddits listed next to it. Rules not listed here will be applied to all
# subreddits in trackingSubreddits.
subredditRestrictions = {}
for rule in listOfCommentRules.update(listOfSubmissionRules):
    try:
        #this gets the rule's section and subreddit restrictions, and stores them in the dictionary
        subredditRestrictions[rule] = config.get(listOfCommentRules.update(listOfSubmissionRules)[rule], 'SubredditRestrictions').strip().split(",")
    except Exception:
        pass

#Allow these rules to apply more than once in a single thread.
metaRule1Exemptions = []
for rule in config.get('Rules', 'MetaRule1Exemptions').strip().split(","):
    try:
        metaRule1Exemptions.append(eval(rule))
    except NameError:
        print 'Error when parsing Meta-rule 1 exemptions: rule \''+rule+'\' does not exist.'

#Allow these rules to reply to the bot itself, or to users in usersWeveRepliedTo.
metaRule2Exemptions = []
for rule in config.get('Rules', 'MetaRule2Exemptions').strip().split(","):
    try:
        metaRule1Exemptions.append(eval(rule))
    except NameError:
        print 'Error when parsing Meta-rule 2 exemptions: rule \''+rule+'\' does not exist.'

metaRule2Whitelist = config.get('Rules', 'MetaRule2Whitelist').strip().split(",")

throttlingExemptions = config.get('Rules', 'ThrottlingExemptions').strip().split(",")

DELETION_DELAY = config.get('Rules', 'DeletionDelay').strip().split(",") #In seconds.
# After the specified delay, a comment must have AT LEAST this
# much karma in order to escape deletion.
DEFAULT_DELETION_THRESHOLD = config.get('Rules', 'DefaultDeletionThreshold').strip().split(",")

deletionThresholds = {}
for rule in listOfCommentRules.update(listOfSubmissionRules):
    try:
        #this gets the rule's section and deletion threashold, and stores them in the dictionary
        deletionThreasholds[rule.__name__] = config.get(listOfCommentRules.update(listOfSubmissionRules)[rule], 'DeletionThreshold')
    except Exception:
        pass

###################### END CONFIGURATION LISTS #######################
######################################################################






######################################################################
################## BEGIN DARK ATHEIST PYTHON MAGIC ###################


def loadDictionary(fileName, format):
	output = {}
	file = open(fileName)
	for line in file.readlines():
		array = line.split()
		k = array[0]
		if format == "string":
			value = array[1]
		elif format == "list":
			value = array[1:]
		elif format == "float":
			value = float(array[1])
		output[k] = value
	file.close()
	return output

#This should always be wrapped in try/except, in case the comment was deleted or something.
def getCommentFromToken(r, token):
	splitToken = token.split("#")
	threadID = splitToken[0]
	commentID = splitToken[1]
	return praw.objects.Submission.from_url(r, "http://www.reddit.com/r/all/comments/"+threadID+"/_/"+commentID).comments[0]

def loadBotConversations():
	output = {}
	file = open("botConversations.txt")
	for line in file.readlines():
		array = line.split()
		tailID = array[0]
		try:
			headComment = getCommentFromToken(r, array[2])
		except:
			print "Couldn't load botConversation", array
			continue
		tailAuthor = array[1]
		headAuthor = array[3]
		output[tailID] = [tailAuthor, headComment, headAuthor]
	return output

def dumpBotConversations():
	file = open("botConversations.txt","w")
	file.write("")
	file.close()
	file = open("botConversations.txt","a")
	for tailID in botConversations:
		if botConversations[tailID]:
			array = botConversations[tailID]
			file.write(tailID + " " + array[0] + " " + array[1].submission.id + "#" + array[1].id + " " + array[2]+"\n")
	file.close()
	print "botConversations successfully dumped."


threadsWeveRepliedTo = loadDictionary("threads.txt", "list")
repliesWeveMade      = loadDictionary("replies.txt", "list")
commentPlaceholders  = loadDictionary("commentPlaceholders.txt", "string")
submissionPlaceholders=loadDictionary("submissionPlaceholders.txt", "string")
throttlingFactors    = loadDictionary("throttlingFactors.txt", "float")




for rule in listOfCommentRules:
	ruleName = listOfCommentRules[rule]
	if ruleName not in throttlingFactors: throttlingFactors[ruleName] = 1
for rule in listOfSubmissionRules:
	ruleName = listOfSubmissionRules[rule]
	if ruleName not in throttlingFactors: throttlingFactors[ruleName] = 1


feederPlaceholder = ""
file = open("feederPlaceholder.txt")
feederPlaceholder = file.readlines()[0]
file.close()


feederThreadsWeveAnswered = []
feederRepliesWeveMade = []
file = open("feederHistory.txt")
lines = file.readlines()
feederThreadsWeveAnswered = lines[0].split()
feederRepliesWeveMade = lines[1].split()
usersWeveRepliedTo = lines[2].split() #This has nothing to do with the feeder,
#but I'm putting it here so I don't have to make another file.
file.close()



def dumpDictionary(dictionary, fileName, format):
	file = open(fileName,"w")
	file.write("")
	file.close()
	file = open(fileName,"a")
	for k in dictionary:
		file.write(k+" ")
		if format == "list":
			for li in dictionary[k]:
				file.write(li+" ")
		elif format == "string":
			file.write(str(dictionary[k]))
		file.write("\n")
	file.close()


def dumpMemory():
	try:
		dumpDictionary(threadsWeveRepliedTo, "threads.txt", "list")
		dumpDictionary(repliesWeveMade, "replies.txt", "list")
		dumpDictionary(commentPlaceholders, "commentPlaceholders.txt", "string")
		dumpDictionary(submissionPlaceholders, "submissionPlaceholders.txt", "string")

		file = open("feederPlaceholder.txt","w")
		file.write(feederPlaceholder)
		file.close()

		file = open("feederHistory.txt","w")
		file.write(string.join(feederThreadsWeveAnswered," "))
		file.write("\n")
		file.write(string.join(feederRepliesWeveMade," "))
		file.write("\n")
		file.write(string.join(usersWeveRepliedTo," "))
		file.close()

		print "Memory successfully dumped."
	except Exception, ex:
		print "Error dumping memory:", ex


def dumpThrottlingFactors():
	dumpDictionary(throttlingFactors, "throttlingFactors.txt", "string")
	print "Throttling factors successfully dumped."



delayedComments = []
nextDelayedComments = []

deletionQueue = []
botAccusations = deque([])



def nameOfRule(ruleFunction):
	if ruleFunction in listOfCommentRules:
		return listOfCommentRules[ruleFunction]
	elif ruleFunction in listOfSubmissionRules:
		return listOfSubmissionRules[ruleFunction]
	else:
		print "WARNING: UNKNOWN RULE TYPE!"
		return None





def makeComment(reply, ruleFunction, replyee): # Actually makes both comments and submissions.
	if type(reply).__name__ == "function":
		myReply = reply()
	elif type(reply[1]).__name__ == "Submission":
		myReply = reply[1].add_comment(reply[0])
	elif type(reply[1]).__name__ == "Comment":
		myReply = reply[1].reply(reply[0]) #DAE reply?
	else:
		print "WARNING: UNKNOWN REPLY TYPE! EXCEPTION WILL SOON BE RAISED!"

	if type(myReply).__name__ == "Comment":
		thread = myReply.submission.id
		deletionQueue.append((myReply, time.time()))
		#We will check this some number of comments later, and delete it if it gets too many downvotes.
	elif type(myReply).__name__ == "Submission":
		thread = myReply.id
	else:
		raise Exception("Error: myReply is of unknown type: "+type(myReply).__name__)

	n = nameOfRule(ruleFunction)
	threadsWeveRepliedTo[n].append(thread)
	repliesWeveMade[n].append(thread+"#"+myReply.id)
	usersWeveRepliedTo.append(replyee)
	print "Successfully commented!", myReply.permalink


#TODO: figure out how to add "replyee" to usersWeveRepliedTo only after the comment posts.
def attemptComment(reply, ruleFunction, threadID, delaying=False):
	if ruleFunction not in metaRule1Exemptions and threadID in threadsWeveRepliedTo[nameOfRule(ruleFunction)]:
		print "Meta-Rule #1 of Bravery: Never use the same rule twice in one thread."
	else:
		if type(reply).__name__=="tuple" and len(reply)==2:
			replyee = str(reply[1].author)
		else:
			replyee = ""
		if replyee != "" and ruleFunction not in metaRule2Exemptions and (replyee == USERNAME or (replyee in usersWeveRepliedTo and replyee not in metaRule2Whitelist)):
			print "Meta-Rule #2 of Bravery: Never reply to yourself or to people we've already replied to."
		else:
			if not delaying and delayedComments:
				#There are already comments in the queue. Add this to the end.
				delayedComments.append((reply, ruleFunction, threadID))
				print "Comment has been queued because there are already comments waiting."
			else:
				try:
					makeComment(reply, ruleFunction, replyee)
				except Exception, ex:
					if "you are doing that too much. try again in" in str(ex):
						if delaying:
							nextDelayedComments.append((reply, ruleFunction, threadID))
							print "We still couldn't post the comment. Deferred to the next round.", str(ex)
						else:
							delayedComments.append((reply, ruleFunction, threadID))
							print "Comment has been delayed.", str(ex)
					else:
						print "Something went wrong! We will not try this comment again.", ex




# WARNING: TOO META FOR WORK
def implementRule(ruleFunction, isCommentTracker):
	def implementImplementation(comment=None,
								body=None,
								submission=None,
								is_self=None,
								title=None,
								url=None,
								selftext=None):
		if isCommentTracker:
			reply = ruleFunction(comment,body) #or
		else:
			reply = ruleFunction(submission,is_self,title,url,selftext)
		if not reply:
			pass # No rules apply.
		else:
			if isCommentTracker:
				threadID = comment.submission.id #or
			else:
				threadID = submission.id
			attemptComment(reply, ruleFunction, threadID)

	if isCommentTracker:
		def implementation(comment,body):
			implementImplementation(comment,body)
	else:
		def implementation(submission,is_self,title,url,selftext):
			implementImplementation(None,None,submission,is_self,title,url,selftext)
	return implementation



def checkSubreddit(sr, isCommentTracker):
	#It doesn't make sense to get submissions from @ORANGERED:
	if not isCommentTracker and sr == "@ORANGERED": return
	try:
		noun = ("comments" if isCommentTracker else "submissions")
		print "Checking subreddit for", noun, ":", sr
		applicablePlaceholders = commentPlaceholders if isCommentTracker else submissionPlaceholders

		if sr in applicablePlaceholders:
			ph = applicablePlaceholders[sr]
		else:
			ph = None

		if sr == "@ORANGERED":
			#print "Getting orangereds"
			posts = r.get_inbox()
			postsList = []
			i = 0
			for x in posts:
				i+=1
				if type(x).__name__ == "Comment" and str(x.author)!="SOTB-bot":
					postsList.append(x)
				if i>10 or x.id == ph:
					break
		else:
			if sr in bannedSubreddits:
				subreddit = r2.get_subreddit(sr)
			else:
				subreddit = r.get_subreddit(sr)
			if isCommentTracker:
				if sr == "askreddit":
					lim = 800
				elif sr == "Braveryjerk":
					lim = 50
				else:
					lim = 500
				posts = subreddit.get_comments(place_holder=ph, limit=lim)
			else:
				posts = subreddit.get_new(place_holder=ph,limit=40)
			postsList = [x for x in posts]

		if not postsList:
			print "Nothing."
			dumpMemory()
			return

		applicablePlaceholders[sr] = postsList[0].id
		postsList = postsList[:-1]
		print len(postsList), noun, "from", sr

		for post in postsList:
			if isCommentTracker:
				comment = post
				body = comment.body
			else:
				submission = post
				is_self = submission.is_self
				title = submission.title
				url = submission.url
				selftext = submission.selftext

			for (rule, implementedRule) in (implementedCommentRules if isCommentTracker else implementedSubmissionRules):
				if( (sr in trackingSubreddits) and \
					(rule not in subredditRestrictions or sr in subredditRestrictions[rule]) ) or \
				  ( (sr in specialSubreddits) and \
					(rule in subredditRestrictions and sr in subredditRestrictions[rule])
					):
					if (random.random() <= throttlingFactors[nameOfRule(rule)]):
						if isCommentTracker:
							implementedRule(comment,body)
						else:
							implementedRule(submission,is_self,title,url,selftext)

	except Exception, ex:
		print "An error occurred:", ex

	dumpMemory()



def is_comment(url):
	url_suffix = url[url.index("reddit.com/r/")+13:]
	slashed = url_suffix.split("/")
	if len(slashed) >= 5 and slashed[4] != "":
		return True
	else:
		return False

def processFeeder(submission):
	callbackText = "Mysterious error. Something went seriously wrong if you see this."
	title = submission.title
	feederThreadID = submission.id
	if not submission.is_self:
		print "Feeder post is not a self-post. Do nothing."
	elif feederThreadID in feederThreadsWeveAnswered:
		print "We've already answered this, but for some reason we're looking at it again."
	elif title[:4] == "http":
		try:
			url = title
			if "?context=" in url:
				url = url[:url.index("?context=")]
			try:
				linked_thing = praw.objects.Submission.from_url(r, url)
			except:
				raise Exception("Couldn't parse your title. Please ensure that the title of your post is the URL of a Reddit comment thread or comment permalink, and try again.")

			iscomment = is_comment(url)
			if iscomment:
				linked_thing = linked_thing.comments[0]

			selftext = submission.selftext
			if not selftext:
				raise Exception("You must enter something for the self-text. Please try again.")
			else:
				#if iscomment: x = linked_thing.reply(selftext)
				#else: x = linked_thing.add_comment(selftext)
				registration = str(submission.author)+"!FEEDER"
				x = forceComment(selftext, linked_thing, registration)
				if not x:
					raise Exception("Error in commenting. Please try again.")
				permalink = x.permalink
				identifyingToken = x.submission.id + "#" + x.id
				feederThreadsWeveAnswered.append(feederThreadID)
				feederRepliesWeveMade.append(identifyingToken)
				innerText = random.choice([
					"Here you go, brave sir/madam",
					"Literally This",
					"SO BRAVE",
					"I have LITERALLY posted this",
				])
				callbackText = "["+innerText+"]("+permalink+")"
		except Exception, ex:
			callbackText = "Error: " + str(ex)

		try:
			y = submission.add_comment(callbackText)
			print "Posted callback:", y.permalink
		except Exception, ex:
			print "Error in posting callback. User's out of luck; there's nothing else we can do.", ex
	else:
		print "Not an http self-post."




def splitArrayByElement(array, splitter):
	output = []
	current = []
	for element in array:
		if element == splitter:
			output.append(current)
			current = []
		else:
			current.append(element)
	output.append(current)
	return output


r = praw.Reddit(user_agent="Bravery bot 3.0 by /u/"+USERNAME)
r.login(username=USERNAME, password=PASSWORD)

r2 = praw.Reddit(user_agent="Bravery bot 3.0 by /u/"+USERNAME2)
r2.login(username=USERNAME2, password=PASSWORD)

botConversations = loadBotConversations()


# Before we start, update the throttlingFactors based on the karma totals,
# not from the previous day, but from the day before that.

if "noassess" not in sys.argv:
	#"""
	DOWN_INCREMENT = 0.5
	UP_INCREMENT = 1.2
	print "Updating throttling factors based on yesterday's karma."
	for ruleName in repliesWeveMade:
		if ruleName in throttlingExemptions:
			print ruleName, "is exempt from throttling."
			continue
		if "!" in ruleName:
			print ruleName, "is not a real rule."
			continue
		print "Assessing", ruleName
		splitList = splitArrayByElement(repliesWeveMade[ruleName], "$")
		if len(splitList) >=2:
			yesterday = splitList[-2]
		else:
			yesterday = []
		karma = 0
		for ids in yesterday:
			arr = ids.split("#")
			threadID = arr[0]
			commentID = arr[1]
			url = "http://www.reddit.com/r/all/comments/"+threadID+"/_/"+commentID
			try:
				commentTree = praw.objects.Submission.from_url(r, url).comments
				if commentTree:
					comment = commentTree[0]
					score = int(comment.score)-1
					print "A score of", str(score), "at", url
					karma += score
				else:
					print "Comment has been deleted:", url
			except Exception, ex:
				print "Exception in getting comment. Assume 0.", ex
			#print "Adding entry:", entry
		print ruleName, "has gotten", str(karma), "karma."
		if karma > 0:
			throttlingFactors[ruleName] = min(1.0, throttlingFactors[ruleName]*UP_INCREMENT)
		elif karma < 0:
			throttlingFactors[ruleName] = max(0.0, throttlingFactors[ruleName]*DOWN_INCREMENT)

	print "Done adjusting throttlingFactors."
	dumpThrottlingFactors()

	# Add "$" to the end of each repliesWeveMade list to mark the beginning of a new day.
	for ruleName in repliesWeveMade:
		repliesWeveMade[ruleName].append("$")
	dumpMemory()
	#"""

#Get ready...
implementedCommentRules    = [(rule,implementRule(rule,True))  for rule in listOfCommentRules]
implementedSubmissionRules = [(rule,implementRule(rule,False)) for rule in listOfSubmissionRules]
startTime = time.time()

#Go!
while True:
	print "Start loop."

	try:
		feeder = rBot.get_subreddit("SurvivalOfTheBravest")
		posts = feeder.get_new(place_holder=feederPlaceholder,limit=40)
		postsList = [s for s in posts]

		feederPlaceholder = postsList[0].id
		postsList = postsList[:-1]
		postsList.reverse()

		print "Got " + str(len(postsList)) + " posts from the feeder."

		for post in postsList:
			processFeeder(post)

		print "Done with feeder."
	except Exception, ex:
		print "An exception occurred while processing the feeder:", ex
	dumpMemory()



	delayedComments = nextDelayedComments
	nextDelayedComments = []

	print "Checking comments:"
	for sr in trackingSubreddits:
		checkSubreddit(sr, True)
	for sr in specialSubreddits:
		checkSubreddit(sr, True)


	#"""
	print "Checking submissions:"
	for sr in trackingSubreddits:
		checkSubreddit(sr, False)
	for sr in specialSubreddits:
		checkSubreddit(sr, False)
	#"""

	print "Done with every subreddit."


	if delayedComments:
		print "We will now attempt to make the", len(delayedComments), "delayed comments."
		for (reply, ruleFunction, threadID) in delayedComments:
			attemptComment(reply, ruleFunction, threadID, delaying=True)
		dumpMemory()
		print "Finished with the delayed comments."
	else:
		print "No delayed comments."

	print "Done applying rules."

	print "Checking for comments to delete."
	newDeletionQueue = []
	for (myComment, timestamp) in deletionQueue:
		if time.time() - timestamp > DELETION_DELAY:
			print "Assessing comment:", myComment.permalink
			try:
				refreshedComment = praw.objects.Submission.from_url(r, myComment.permalink).comments[0]
				ruleName = ruleResponsibleForCommentWithID(myComment.id)
				if ruleName in deletionThresholds:
					threshold = deletionThresholds[ruleName]
				else:
					threshold = DEFAULT_DELETION_THRESHOLD
				if refreshedComment.score < threshold:
					print "Deleting comment."
					myComment.delete()
				else:
					print "Comment is spared."
			except:
				print "Comment not found."
		else:
			newDeletionQueue.append((myComment, timestamp))
	deletionQueue = newDeletionQueue
	print "Done deleting comments."

	print "Sleeping..."
	time.sleep(80)

	#Are we done for the day?
	currentTime = time.time()
	if currentTime - startTime > 85500:
		print "Timed out after 23:45."
		break
	else:
		print "Moving on..."




################### END DARK ATHEIST PYTHON MAGIC ####################
######################################################################


#YOLO
#SWAG
#BRAVE
