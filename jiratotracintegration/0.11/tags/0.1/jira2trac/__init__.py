#!/usr/bin/env python3.1
#
# Copyright (c) 2008-2009 The Jira2Trac Project.
# See LICENSE.txt for details.

"""
Import a Jira backup into a Trac database using XML-RPC.

@since: 2008-12-20
"""

import os
import sys
import logging as log

from io import FileIO
from stat import ST_SIZE
from xmlrpc import client
from decimal import Decimal
from datetime import datetime
from xml.parsers import expat
from operator import itemgetter
from socket import error as socketError
from jira2trac.util import create_hash
from jira2trac.util import DisplayProgress


__all__ = ['JiraDecoder', 'TracEncoder']

__version__ = (0, 1)

version = '.'.join(map(lambda x: str(x), __version__))


class JiraDecoder(object):
    """
    Parse a Jira XML backup file.
    """
    def __init__(self, input):
        if input:
            self.input = input
            self.lastComment = None
            self.lastIssue = None
            self.allItems = []
            self.comments = []
            self.issues = []
            self.data = dict()
            self.data['versions'] = []
            self.data['resolutions'] = []
            self.data['projects'] = []
            self.data['priorities'] = []
            self.data['users'] = []
            self.data['issues'] = []
            self.data['components'] = []
            self.data['customFieldValues'] = []
            self.data['eventTypes'] = []
            self.data['attachments'] = []
            self.data['issueTypes'] = []
            self.data['groups'] = []
            self.data['memberships'] = []
            self.data['statuses'] = []
            self.data['actions'] = []
        else:
            raise BaseException("Please specify the 'input' option")

    def parseBackupFile(self):
        """
        Load Jira backup file.
        """
        self.size = Decimal(str(os.stat(self.input)[ST_SIZE]/(1024*1024))
                            ).quantize(Decimal('.01'))

        log.info('Loading Jira backup file: %s (%s MB)' % (self.input, self.size))
        log.info('Processing data...')

        file = FileIO(self.input, 'r').readall()
        p = expat.ParserCreate()
        p.StartElementHandler = self._start_element
        p.EndElementHandler = self._end_element
        p.CharacterDataHandler = self._char_data
        p.Parse(file, 1)

    def showResults(self):
        """
        Display the parse results.
        """       
        categories = ['versions', 'resolutions', 'projects', 'priorities',
                      'components', 'issueTypes', 'statuses', 'groups',
                      'issues', 'attachments', 'users', 'actions']

        for category in categories:
            name = category.title()

            if category == 'issueTypes':
                name = 'Issue Types'

            log.info('  %d %s...' % (len(self.data[category]), name))

        # print a parsed category
        #for item in self.data['projects']:
        #    print(item)
        #    print('%50s - %s - %s - %s' % (item['issue'], item['author'], item['type'],
        #                          item['body']))
                    
    def _addItem(self, category, data, type=None):
        if type == None:
            type = self.allItems

        self.data[category].append(data)
        type.append(data)
        self.category = category

    def _char_data(self, data):
        log.debug('Character data: %s' % repr(data))

        if self.lastComment:
            self._updateItem(data, self.lastComment)
        elif self.lastIssue:
            self._updateItem(data, self.lastIssue)

    def _updateItem(self, data, target):
        if (data != "'\n'") or (data[1:len(data)-1].isspace() == False):
            if target == self.lastComment:
                field = 'body'
            elif target == self.lastIssue:
                field = 'description'

            target[field] += data

    def _end_element(self, name):
        log.debug('End element: %s' % name)
        index = len(self.data[self.category]) - 1

        if name == 'body':
            self.data[self.category][index] = self.lastComment
            self.lastComment = None
        elif name == 'description':
            self.data[self.category][index] = self.lastIssue
            self.lastIssue = None

    def _start_element(self, name, attrs):
        log.debug('Start element: %s %s' % (name, attrs))

        if name == 'Version':
            version = {'number':attrs['name']}
            try:
                version['description'] = attrs['description']
            except KeyError:
                version['description'] = None

            try:
                version['releasedate'] = self.to_datetime(attrs['releasedate'])
            except KeyError:
                version['releasedate'] = 0

            self._addItem('versions', version)

        elif name == 'Resolution':
            resolution = {'name': attrs['name'], 'description': attrs['description'],
                          'id': attrs['id']}
            
            self._addItem('resolutions', resolution)

        elif name == 'Status':
            status = {'id': attrs['id'], 'sequence': attrs['sequence'],
                      'name': attrs['name'], 'description': attrs['description']}

            self._addItem('statuses', status)

        elif name == 'Project':
            project = {'name': attrs['name'], 'owner': attrs['lead'],
                       'description': attrs['description'], 'id': attrs['id']}

            self._addItem('projects', project)

        elif name == 'Priority':
            priority = {'name': attrs['name'], 'description': attrs['description'],
                        'id': attrs['id']}

            self._addItem('priorities', priority)

        elif name == 'OSUser':
            user = {'name': attrs['name'], 'id': attrs['id']}
            
            try:
                user['password'] = attrs['passwordHash']
                self._addItem('users', user)
            except KeyError:
                pass

        elif name == 'Issue':
            issue = {'project': attrs['project'], 'id': attrs['id'],
                     'reporter': attrs['reporter'], 'assignee': attrs['assignee'],
                     'type': attrs['type'], 'summary': attrs['summary'],
                     'priority': attrs['priority'], 'status': attrs['status'],
                     'votes': attrs['votes'], 'key': attrs['key']}

            issue['created'] = self.to_datetime(attrs['created'])

            try:
                issue['resolution'] = attrs['resolution']
            except KeyError:
                issue['resolution'] = 1

            try:
                issue['description'] = attrs['description']
            except:
                issue['description'] = ''

            self._addItem('issues', issue, self.issues)

        elif name == 'Component':
            component = {'project': attrs['project'], 'id': attrs['id'],
                         'name': attrs['name'], 'description': attrs['description'],
                         'owner': attrs['lead']}

            self._addItem('components', component)

        elif name == 'CustomFieldValue' and attrs['customfield'] == '10001':
            customFieldValue = {'issue': attrs['issue'], 'id': attrs['id'],
                                'value': attrs['stringvalue']}

            self._addItem('customFieldValues', customFieldValue)

        elif name == 'EventType':
            eventType = {'id': attrs['id'], 'name': attrs['name'],
                         'description': attrs['description']}

            self._addItem('eventTypes', eventType)

        elif name == 'IssueType':
            issueType = {'id': attrs['id'], 'sequence': attrs['sequence'],
                         'name': attrs['name'], 'description': attrs['description']}

            self._addItem('issueTypes', issueType)

        elif name == 'FileAttachment':
            attachment = {'id': attrs['id'], 'issue': attrs['issue'],
                         'mimetype': attrs['mimetype'], 'filename': attrs['filename'],
                         'filesize': attrs['filesize']}

            attachment['created'] = self.to_datetime(attrs['created'])

            try:
                attachment['author'] = attrs['author']
            except KeyError:
                attachment['author'] = ''

            self._addItem('attachments', attachment)

        elif name == 'OSGroup':
            group = {'id': attrs['id'], 'name': attrs['name']}

            self._addItem('groups', group)

        elif name == 'Action':
            action = {'id': attrs['id'], 'issue': attrs['issue'],
                      'author': attrs['author'], 'type': attrs['type']}

            action['created'] = self.to_datetime(attrs['created'])

            try:
                action['body'] = attrs['body']
            except KeyError:
                action['body'] = ''

            self._addItem('actions', action, self.comments)

        elif name == 'OSMembership':
            membership = {'id': attrs['id'], 'username': attrs['userName'],
                          'groupName': attrs['groupName']}

            self._addItem('memberships', membership)
        
        elif name == 'body':
            self.lastComment = self.comments[len(self.comments)-1]
            self.lastComment['body'] = ''

        elif name == 'description':
            self.lastIssue = self.issues[len(self.issues)-1]
            self.lastIssue['description'] = ''

        # Unused:
        #  - OSCurrentStep
        #  - OSCurrentStepPrev
        #  - OSHistoryStep
        #  - OSHistoryStepPrev
        #  - OSPropertyEntry
        #  - OSPropertyString
        #  - OSWorkflowEntry
        #  - UserAssociation

    def to_datetime(self, timestamp):
        """
        Turn timestamp string into C{datetime.datetime} object.
        """
        return datetime.strptime(timestamp[:-2], '%Y-%m-%d %H:%M:%S')


class TracEncoder(object):
    """
    Import data into remote Trac database using XML-RPC.
    """
    def __init__(self, jiraData, username, password, url, attachments, auth):
        if url:
            self.jiraData = jiraData
            self.url = url
            self.username = username
            self.password = password
            self.attachments = attachments
            self.authentication = auth

            if username is not None and password is not None:
                cred = '%s:%s@' % (username, password)
            else:
                cred = ''

            self.location = "http://%s%s/login/xmlrpc" % (cred, url)
            log.info('%s...' % self.__doc__.strip())

        else:
            raise ValueError("Please specify a value for the 'url' option")

    def importData(self):
        """
        Save all data to the Trac database.
        """
        log.info('Connecting to: %s' % self.location)
        log.info('Attachments location: %s' % self.attachments)
        log.info('Credentials type: %s' % self.authentication)

        self.proxy = client.ServerProxy(self.location, use_datetime=True)

        log.info('Importing data...')
        self._call(self._importVersions)
        self._call(self._importResolutions)
        self._call(self._importPriorities)
        self._call(self._importIssueTypes)
        self._call(self._importMilestones)
        self._call(self._importComponents)
        self._call(self._importStatuses)
        self._call(self._importIssues)

    def importUsers(self):
        """
        Store imported users in a new .htpasswd style file.
        """
        log.info('  %d Users...' % (len(self.jiraData['users'])))

        line = '%s:%s\n'
        output = FileIO(self.authentication, 'w')
        output.write(line % (self.username, create_hash(self.password)))
        
        for user in self.jiraData['users']:
            output.write(line % (user['name'], user['password']))

        output.close()

    def _call(self, func):
        """
        Invoke a method and handle exceptions.
        """
        try:
            func()

        except client.ProtocolError as err:
            log.error("A protocol error occurred!")
            log.error("URL: %s" % err.url)
            log.error("HTTP/HTTPS headers: %s" % err.headers)
            log.error("Error: %d - %s" % (err.errcode, err.errmsg))
            sys.exit()

        except client.Fault as err:
            log.error("A fault occurred!")
            log.error("Fault code: %d" % err.faultCode)
            log.error("Fault string: %s" % err.faultString)

        except socketError as err:
            log.error("A socket error occurred!")
            log.error("Error while connecting: %s" % err)
            sys.exit()

    
    
    def _importVersions(self):
        # get existing versions from trac
        versions = self.proxy.ticket.version.getAll()

        # remove existing versions from trac if necessary
        if len(versions) > 0:
            for version in versions:
                self.proxy.ticket.version.delete(version)

        # show progress bar
        progress = DisplayProgress(len(self.jiraData['versions']),
                                   'Versions')
        
        # import new versions into trac
        for version in self.jiraData['versions']:
            # exclude trailing 'v' from version number
            nr = version['number'][1:]
            desc = version['description']
            date = version['releasedate']
            attr = {'name': nr, 'time': date, 'description': desc}
            self.proxy.ticket.version.create(nr, attr)
            progress.update()

    def _importResolutions(self):
        # get existing resolutions from trac
        resolutions = self.proxy.ticket.resolution.getAll()

        # remove existing resolutions from trac if necessary
        if len(resolutions) > 0:
            for resolution in resolutions:
                self.proxy.ticket.resolution.delete(resolution)

        # show progress bar
        progress = DisplayProgress(len(self.jiraData['resolutions']),
                                    'Resolutions')

        # import new resolutions into trac
        order = 1
        for resolution in self.jiraData['resolutions']:
            name = resolution['name']
            self.proxy.ticket.resolution.create(name, order)
            order += 1
            progress.update()

    def _importPriorities(self):
        # get existing priorities from trac
        priorities = self.proxy.ticket.priority.getAll()

        # remove existing priorities from trac if necessary
        if len(priorities) > 0:
            for priority in priorities:
                self.proxy.ticket.priority.delete(priority)

        # show progress bar
        progress = DisplayProgress(len(self.jiraData['priorities']),
                                   'Priorities')

        # import new priorities into trac
        order = 1
        for priority in self.jiraData['priorities']:
            name = priority['name']
            self.proxy.ticket.priority.create(name, order)
            order += 1
            progress.update()

    def _importIssueTypes(self):
        # get existing issue types from trac
        issueTypes = self.proxy.ticket.type.getAll()

        # remove existing issue types from trac if necessary
        if len(issueTypes) > 0:
            for issueType in issueTypes:
                self.proxy.ticket.type.delete(issueType)

        # show progress bar
        progress = DisplayProgress(len(self.jiraData['issueTypes']),
                                   'Issue Types')

        # import new issue types into trac
        for issueType in self.jiraData['issueTypes']:
            name = issueType['name']
            order = issueType['sequence']
            self.proxy.ticket.type.create(name, order)
            progress.update()

    def _importMilestones(self):
        # get existing milestones from trac
        milestones = self.proxy.ticket.milestone.getAll()

        # seems Jira doesn't support milestones or we never used them
        # so remove all existing milestones from trac
        if len(milestones) > 0:
            for milestone in milestones:
                self.proxy.ticket.milestone.delete(milestone)

    def _importComponents(self):
        # get existing components from trac
        components = self.proxy.ticket.component.getAll()

        # remove existing components from trac if necessary
        if len(components) > 0:
            for component in components:
                self.proxy.ticket.component.delete(component)

        # show progress bar
        progress = DisplayProgress(len(self.jiraData['projects']),
                                   'Components')

        # import new components into trac
        # note: we import jira's projects as components into trac because
        # components in jira are children of projects, and trac doesn't
        # support this type of hierarchy
        for component in self.jiraData['projects']:
            name = component['name']
            owner = component['owner']
            desc = component['description']
            attr = {'name': name, 'owner': owner, 'description': desc}
            self.proxy.ticket.component.create(name, attr)
            progress.update()

    def _importStatuses(self):
        # get existing statuses from trac
        statuses = self.proxy.ticket.status.getAll()

        # Note: ticket.status.delete() and ticket.status.update() aren't working
        # due to a bug in the XML-RPC plugin for Trac, see this link for more
        # information: http://trac-hacks.org/ticket/5268
        # For that reason it's not possible to delete the default Trac statuses
        # so we hardcode and manually map the statuses
        self.jiraData['statuses'][0]['name'] = statuses[3] # open/new
        self.jiraData['statuses'][1]['name'] = statuses[0] # in progress/accepted
        self.jiraData['statuses'][2]['name'] = statuses[4] # reopened/reopened
        self.jiraData['statuses'][3]['name'] = statuses[2] # resolved/closed
        self.jiraData['statuses'][4]['name'] = statuses[2] # closed/closed

        log.info('  %d Statuses...' % len(self.jiraData['statuses']))

    def _importIssues(self):
        # show progress bar
        progress = DisplayProgress(len(self.jiraData['issues']),
                                   'Issues')
        
        # import new issues into trac
        for issue in self.jiraData['issues']:
            # TODO: version
            description = issue['description']            
            reporter = issue['reporter']
            owner = issue['assignee']
            summary = issue['summary']
            time = issue['created']
            status = self._getItem(issue['status'], 'statuses')
            component = self._getItem(issue['project'], 'projects')
            resolution = self._getItem(issue['resolution'], 'resolutions')
            type = self._getItem(issue['type'], 'issueTypes')
            priority = self._getItem(issue['priority'], 'priorities')
            comments = self._getComments(issue['id'])
            attachments = self._getAttachments(issue['id'])

            attr = {'reporter': reporter, 'owner': owner, 'component': component,
                    'type': type, 'priority': priority, 'status': status}

            if resolution is not None:
                attr['resolution'] = resolution

            # import issue in trac
            id = self.proxy.ticket.create(summary, description, time, attr)

            # import associated comments for issue in trac
            cnum = 0
            for comment in comments:
                cnum += 1
                self.proxy.ticket.update(id, comment['body'], comment['created'],
                                         comment['author'], cnum+1)

            # import associated attachments for issue in trac
            for attachment in attachments:
                author = attachment['author']
                description = ''
                key = issue['key']
                created = attachment['created']
                filename = attachment['filename']
                path = self._getAttachmentPath(attachment['attachmentId'], key,
                                               filename)
                if os.path.exists(path):
                    file = open(path, 'rb').read()
                    data = client.Binary(file)
                    self.proxy.ticket.putAttachment(id, filename, description,
                                            data, author, created, False)
            progress.update()

        log.info('  %d Actions' % len(self.jiraData['actions']))
        log.info('  %d Attachments' % len(self.jiraData['attachments']))

    def _getAttachmentPath(self, id, key, filename):
        project = key.rsplit('-')[0]
        file = '%d_%s' % (id, filename)
        path = os.path.join(self.attachments, project, key, file)
        return path

    def _getItem(self, id, target, field='name'):
        for d in self.jiraData[target]:
            if d['id'] == id:
                return d[field]

    def _getComments(self, id):
        # grab associated comments for issue
        comments = []
        for action in self.jiraData['actions']:
            if action['issue'] == id:
                body = action['body']
                created = action['created']
                author = action['author']
                comment = {'id': action['issue'], 'body': body,
                           'created': created, 'author': author,
                           'commentId': int(action['id'])}
                comments.append(comment)

        # sort comments with oldest id first
        return sorted(comments, key=itemgetter('commentId'), reverse=True)

    def _getAttachments(self, id):
        # grab associated attachments for issue
        attachments = []
        for attachment in self.jiraData['attachments']:
            if attachment['issue'] == id:
                mimetype = attachment['mimetype']
                created = attachment['created']
                author = attachment['author']
                filename = attachment['filename']
                filesize = attachment['filesize']
                att = {'id': attachment['issue'], 'mimetype': mimetype,
                        'created': created, 'author': author,
                        'attachmentId': int(attachment['id']),
                        'filename': filename, 'filesize': filesize}
                attachments.append(att)

        # sort attachments with oldest id first
        return sorted(attachments, key=itemgetter('attachmentId'), reverse=False)


if __name__ == "__main__":
    from jira2trac.scripts import run
    run()
