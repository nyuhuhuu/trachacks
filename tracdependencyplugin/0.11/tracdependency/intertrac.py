# -*- coding: utf-8 -*-
import re
import os.path

from genshi.builder import tag
from genshi.filters.transform import Transformer

from trac.core import *
from trac.web import IRequestHandler
from trac.web.chrome import INavigationContributor, ITemplateProvider, add_ctxtnav
from trac.web.api import IRequestFilter, ITemplateStreamFilter
from trac.ticket.model import Ticket

from trac.env import open_environment

TICKET_CUSTOM = "ticket-custom"

class InterTrac:

    def load_intertrac_setting(self):
        # interTracの設定を取得します．
        self.intertracs0 = {}
        self.summary_label = self.config.get(TICKET_CUSTOM,"summary_ticket.label")
        self.dependencies_label = self.config.get(TICKET_CUSTOM,"dependencies.label")
        for key, value in self.config.options('intertrac'):
            # オプションの数のループを回り，左辺値の.を探します．
            idx = key.rfind('.')  
            if idx > 0: # .が無い場合はショートカットですが無視します
                # .があった場合の処理
                # 左辺値を分割します
                prefix, attribute = key[:idx], key[idx+1:]
                # すでにあるものをとってきます無ければ新規で作成
                intertrac = self.intertracs0.setdefault(prefix, {})
                # 左辺値のピリオド以降をキーで右辺値を登録
                intertrac[attribute] = value
                # プロジェクト名を設定します．(注：すべて小文字になっている) 
                intertrac['name'] = prefix

    def __get_projects(self):
        return self.intertracs0

    def __get_subsequentticket_other_prj(self,ids):
        sql = ("SELECT id, type, summary, owner, description, status from ticket t "
                    "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'dependencies' "
                    "WHERE (c.value = '%s' or c.value like '%s(%%' or c.value like '%s,%%' or "
                    " c.value like '%%, %s(%%' or c.value like '%%, %s,%%' or "
                    " c.value like '%%,%s(%%' or c.value like '%%,%s,%%' or "
                    " c.value like '%%, %s' or c.value like '%%,%s')" % (ids, ids, ids, ids, ids, ids, ids, ids, ids))
        return sql
        
    def __get_subsequentticket(self,ids):
        sql = ("SELECT id, type, summary, owner, description, status from ticket t "
                    "JOIN ticket_custom c ON c.ticket = t.id AND c.name = 'dependencies' "
                    "WHERE "
                    "(c.value = '%s' or c.value like '%s(%%' or c.value like '%s,%%' or "
                    " c.value like '%%, %s(%%' or c.value like '%%, %s,%%' or "
                    " c.value like '%%,%s(%%' or c.value like '%%,%s,%%' or "
                    " c.value like '%%, %s' or c.value like '%%,%s' or "
                    " c.value = '#%s' or c.value like '#%s(%%' or c.value like '#%s,%%' or "
                    " c.value like '%%, #%s(%%' or c.value like '%%, #%s,%%' or "
                    " c.value like '%%,#%s(%%' or c.value like '%%,#%s,%%' or "
                    " c.value like '%%, #%s' or c.value like '%%,#%s')" % (ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids, ids))
        return sql
        
    def __get_subticket_other_prj(self, id_l):
        # InterTrac形式で指定したidを親に指定しているチケットのクエリ文字列を返す
        # id_l InterTrac形式のチケットid
        sql = ("SELECT id, type, summary, owner, description, status from ticket t "
                    "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'summary_ticket' "
                    "WHERE a.value = '%s'" % id_l)
        return sql

    def __get_subticket(self, id_num):
        # 自プロジェクト内で指定したidを親に指定しているチケットのクエリ文字列を返す
        # id_num チケットのid（数値）
        sql = ("SELECT id, type, summary, owner, description, status from ticket t "
                    "JOIN ticket_custom a ON a.ticket = t.id AND a.name = 'summary_ticket' "
                    "WHERE a.value = '#%s' or  a.value = '%s'" % (id_num, id_num))
        return sql

    def __get_tickets_point_to(self, sql, sql_i):
        # InterTrac設定しているプロジェクトすべてを検索する必要がある,
        # 後続チケットまたは，子チケットへのリンクを作ります．
        links = []
        intertracs0 = self.__get_projects()
        # すべてのinterTrc設定を回りサブチケットまたは後続チケットを探します．まずはInterTrac形式の指定のもの
        for prefix in intertracs0:
            intertrac = intertracs0[prefix]
            path = intertrac.get('path', '')
            try:
                if self.__get_project_name() == intertrac['label']:
                    cursor = self.env.get_db_cnx().cursor()
                    cursor.execute(sql_i + " union " + sql)
                    id_prefix = '#'
                else:
                    cursor = open_environment(path, use_cache=True).get_db_cnx().cursor()
                    cursor.execute(sql)
                    id_prefix = intertrac['label'] + ':#' + str(id)
                for id, type, summary, owner, description, status in cursor:
                    url = intertrac.get('url', '') + '/ticket/' + str(id)
                    dep_url = intertrac.get('url', '') + '/dependency/ticket/' + str(id)
                    ticket = id_prefix + str(id)
                    links.append({'ticket':ticket, 'title':summary, 'url':url, 'dep_url':dep_url, 'status':status})
                    # links.append({'title':summary, 'url':url, 'dep_url':dep_url, 'status':status})
            except Exception, e:
                pass
            # オープンできない場合もあるのでエラー処理が必要
        return links

    def get_info_tickets_point_to(self, tkt_id):
        # 自分自身を指定しているチケットを検索する
        # tkt_idはチケット番号
        tkt_id_l = self.__get_project_name() + ':#' + tkt_id
        sub_ticket = self.__get_tickets_point_to(self.__get_subticket_other_prj(tkt_id_l), self.__get_subticket(tkt_id)) 
        subsequentticket = self.__get_tickets_point_to(self.__get_subsequentticket_other_prj(tkt_id_l), self.__get_subsequentticket(tkt_id)) 
        return sub_ticket, subsequentticket

    def __linkify_ids_b(self, ids, label1):
        # チケットの表示のページでinterTracリンクの表示するための元を作る
        # 先行、親など指定しているidを検索する
        data = []
        if ids is None:
            return data
        tickets = ids.split(',') #なにもない場合はエラーになるのでifが必要
        data.append(label1)
        for ticket in tickets:
            t = self.__get_intertrac_ticket(ticket, True)
            error = t['error']
            if error is None:
                tkt = t['ticket']
                status = tkt['status']
                title1 = tkt['summary']
                u = t['url']
                id = t['id']
                url = u + u'/ticket/' + id
                data.append(tag.a('%s'%ticket, href=url, class_='%s ticket'%status, title=title1))
                # 複数ある場合は", "を追加する
                data.append(', ')
        if data:
            # 最後のカンマを削除する．
            del data[-1]
        data.append(tag.br())
        return data

    def __get_intertrac_ticket(self, ticket, dep_en):
        # 指定されたInterTrac形式のチケット名から情報を取得する
        # 問題があった場合はエラーを返す．
        current_project_name = self.__get_project_name()
        intertracs0 = self.__get_projects()
        if ticket:
            ticket = ticket.strip() # 前後の空白を削除します
            idx = ticket.rfind(':#') # プロジェクト名とチケット番号に分割します
            if idx > 0: # InterTrac ticket
                current_project = False
                project_name, id = ticket[:idx], ticket[idx+2:]
                # プロジェクト名が存在するか確認する
                try:
                    intertrac = intertracs0[project_name.lower()]
                except Exception, e: # 存在していない場合は例外が発生する
                    return {'error':' project %s does not exist.'% project_name}
            else: # This ticket is in same project.
                current_project = True
                project_name = current_project_name
                if ticket.rfind('#') == 0:
                    id = ticket[1:]
                else:
                    id = ticket
            if id != "":
                # 依存関係を指定しているか確認する 例:(FF)
                idx = id.rfind('(')
                if idx > 0:
                    # 指定されていたならそれはidに含まない
                    if dep_en == False:
                        #依存関係を使用しない場合でカッコがあった場合は
                        return {'error':'This field can not have dependency.'}
                    id, dep = id[:idx], id[idx+1:]
                    #依存関係に問題がないかの確認が必要
                    if dep.startswith('FF')==False and dep.startswith('FS')==False and dep.startswith('SF')==False and dep.startswith('SS')==False:
                        return {'error':'Unknown type of dependency.'}
                else:
                    dep = ''
                try:
                    # InterTracの設定のキーは小文字
                    intertrac = intertracs0[project_name.lower()]
                    path = intertrac.get('path', '')
                    project = open_environment(path, use_cache=True)
                    tkt = Ticket(project, id)
                except Exception, e:
                    return {'error':'There is no ticket %s(%s,%s).'%(ticket, project_name, id)}
            else: #チケットに何も入っていない
                return {'error':'Many comma are in this field.'}
            return {'name':project_name+':#'+id, 'id':id, 'project':project, 'url':intertrac.get('url', ''), 'project_name':project_name, 'dependency':dep, 'error':None, 'ticket':tkt}
        else:
            return {'error': 'Ticekt    not exists'}

    def __validate_outline_b(self, ticket, sub_ticket, leaf_id):
        # tkt:InterTrac形式のチケット名
        # project_name:葉チケットのプロジェクト名
        # leaf_id:葉チケットのID
        # 戻り値:エラー文字列
        self.log.debug("__validate_outline_b0010 ticket=%s, sub_ticket=%s, leaf_id=%s" , ticket, sub_ticket, leaf_id)
        error = []
        if ticket:
            ticket = ticket.strip() # 前後の空白を削除します
        if ticket == leaf_id:
            return 'Ticket(%s)\'s summary ticket is this ticket'%sub_ticket
        t = self.__get_intertrac_ticket(ticket, False)
        error = t['error']
        if error is None:
            tkt = t['ticket']
            ticket = tkt['summary_ticket']
            if ticket is None: #このifいらなくないか
                pass
            else:
                if ticket == '':
                    pass
                else:
                    return self.__validate_outline_b(ticket, t['name'],leaf_id)
        return None

    def validate_outline(self, tkt, id):
        # tkt:InterTrac形式のチケット名
        # project_name:葉チケットのプロジェクト名
        # id:チケットのID
        # 戻り値:エラー文字列のリスト
        errors = []
        project_name = self.__get_project_name()
        self.log.debug("validate_outline0010 project_name=%s tkt=%s id=%s" , project_name, tkt, id)
        t = self.__get_intertrac_ticket(tkt, False)
        error = t['error']
        if error is None:
            leaf_id = project_name + u':#' + str(id)
            self.log.debug("validate_outline0020 leaf_id=%s" , leaf_id)
            e = self.__validate_outline_b(tkt, leaf_id, leaf_id)
            if e is None:
                pass
            else:
                errors.append((self.summary_label, e))
        return errors

    def validate_ticket(self, ids, field_name, dep_en):
        # ids:カスタムフィールドに入っている値そのままです．
        # field_name: エラーを表示するためのフィールド名
        # dep_en: 親チケットを指定している場合はTrueになります．
        errors = []
        #リンクが正しいか確認します．
        if ids is None: #idになにも入ってない場合はエラーになるのでifが必要
            return errors
        if ids == '': #idになにも入ってない場合はエラーになるのでifが必要
            return errors
        # self.log.debug("test_link = %s" % ids)
        # カンマで分割します．
        tickets = ids.split(',')
        for ticket in tickets: # 分割した文字列でループをまわります．
            # 一つ一つのチケットのリンクに問題がないか確認します．
            t = self.__get_intertrac_ticket(ticket, dep_en)
            error = t['error']
            if error: # エラーがなければ
                errors.append((field_name, error))
                continue
        return errors

    def linkify_ids(self, ids, label1, label2, tickets2):
        # チケットの表示のページでinterTracリンクの表示するための元を作る
        data = self.__linkify_ids_b(ids, label1)
        data.append(label2)
        for ticket in tickets2:
            tkt = ticket['ticket']
            url = ticket['url']
            status = ticket['status']
            title1 = ticket['title']
            data.append(tag.a('%s'%tkt, href=url, class_='%s ticket'%status, title=title1))
            data.append(', ')
        if data:
            # リストになにもない場合はラベル，ある場合は最後のカンマを削除する．
            del data[-1]
        return tag.span(*data)

    def get_link(self, ids):
        links = []
        if ids is None: #idになにも入ってない場合はエラーになるのでifが必要
            return links
        tickets = ids.split(',')
        for ticket in tickets:
            t = self.__get_intertrac_ticket(ticket, True)
            error = t['error']
            if error is None:
                tkt = t['ticket']
                status = tkt['status']
                title = tkt['summary']
                url = t['url'] + '/ticket/' + t['id']
                dep_url = t['url'] + '/dependency/ticket/' + t['id']
                links.append({'ticket':ticket, 'title':title, 'url':url, 'dep_url':dep_url, 'status':status})
                # link = links.append({'title':title, 'url':url, 'dep_url':dep_url, 'status':status})
            else:
                continue
        return links

    def __get_project_name(self):
        return self.project_label

