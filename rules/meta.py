#Meta-rules (and meta code) to make some things work.
#May be removing some of the more specialised rules later, such as orangered megathread.


# Helper function:
# Suspend all processes for 21 minutes or until
# the comment is successfully posted. If it is,
# return it. If it isn't, return None.
# Use this function sparingly.
def forceComment(text, thingToReplyTo, registration="!UNKNOWN"):
	for i in range(21):
		try:
			if type(thingToReplyTo).__name__ == "Comment":
				result = thingToReplyTo.reply(text)
			elif type(thingToReplyTo).__name__ == "Submission":
				result = thingToReplyTo.add_comment(text)
			else:
				print "Error in forceComment: thingToReplyTo is of an unrecognized type"
				return None
			print "Successfully forced comment:", result.permalink
			submissionID = result.submission.id
			commentID = result.id
			token = submissionID + "#" + commentID
			if registration in threadsWeveRepliedTo:
				threadsWeveRepliedTo[registration].append(submissionID)
			else:
				threadsWeveRepliedTo[registration] = [submissionID]
			if registration in repliesWeveMade:
				repliesWeveMade[registration].append(token)
			else:
				repliesWeveMade[registration] = [token]
			return result
		except Exception, e:
			if "Forbidden" in str(e):
				print "Unforceable error:", e
				return None
			print "Error in forceComment. Trying again in 60 seconds:", e
			time.sleep(60)
	print "After 21 minutes we still couldn't force the comment. Giving up."
	return None



# Restrict to @ORANGERED
# Bypasses meta-rules, because it doesn't actually make any comments.
def botLogic(comment, body):
	lc = body.lower()
	if " bot " in lc or " bot?" in lc or " bot," in lc or " bot." in lc or " bot!" in lc or "bot logic" in lc or "automated" in lc:
		accuser = str(comment.author)
		if accuser != USERNAME:
			for tailID in botConversations:
				if botConversations[tailID] and accuser in botConversations[tailID]:
					#This may be a little too strict.
					print "Bot accuser is already participating in a conversation elsewhere."
					return None
			print "Bot accusation detected. Initiate a conversation at the next opportunity."
			botAccusations.append((comment,body))
	return None


# Set a very low initial throttling factor so that this
# takes one or two rounds to be invoked.
def botConversationInitiator(comment,body):
	if (False or random.randint(0,1000) == 1) and botAccusations:
		(c,b) = botAccusations[0]
		# Don't initiate the conversation in the same thread,
		# and don't do it to ourselves (which would be really bad).
		# Also, don't do it to the same person who made the accusation.
		tailAuthor = str(comment.author)
		headAuthor = str(c.author) #The username of the accuser.
		if c.submission != comment.submission and tailAuthor!=USERNAME and tailAuthor!=headAuthor:
			successfulComment = forceComment(b,comment,"botConversationInitiator")
			if successfulComment:
				botConversations[successfulComment.id] = [tailAuthor, c, headAuthor]
				dumpBotConversations()
				botAccusations.popleft()
	return None



# Restrict to @ORANGERED
# If someone replies to a bot accusation conversation, continue the conversation.
# This rule bypasses the normal comment regulators.
def botConversationListener(comment,body):
	tailID = comment.parent_id[3:]
	if tailID in botConversations:
		#Someone just replied to our end of the bot conversation!
		information = botConversations[tailID]
		tailAuthor = information[0]
		headComment = information[1]
		headAuthor = information[2]
		thisCommentAuthor = str(comment.author)
		if thisCommentAuthor == tailAuthor:
			successfulComment = forceComment(body, headComment, "botConversationListener")
			if successfulComment:
				botConversations[tailID] = None
				botConversations[successfulComment.id] = [headAuthor,comment,thisCommentAuthor]
				dumpBotConversations()
		else:
			print "this isn't part of the bot conversation because it's not by the same person."
	return None


# helper function
def ruleResponsibleForCommentWithID(commentID):
	for ruleName in repliesWeveMade:
		replies = repliesWeveMade[ruleName]
		for rep in replies:
			if commentID in rep:
				return ruleName
	return "!NONE"



rBot = praw.Reddit(user_agent="Bravery bot 3.0 utility handler by /u/SOTB-bot")
rBot.login(username="SOTB-bot", password=PASSWORD)


orangeredMegathread = praw.objects.Submission.from_url(rBot, "http://www.reddit.com/r/SurvivalOfTheBravest/comments/1hk7a5/orangered_megathread_3/")
def orangeredViewer(comment, body):
	ruleName = ruleResponsibleForCommentWithID(comment.parent_id[3:])
	preface = "["+str(comment.author)+" responds to "+ruleName+"]("+comment.permalink+"?context=1):\n\n---\n\n"
	return (preface+body, orangeredMegathread)
