<?cs include "my_macros.cs" ?>

<h2>Forums</h2>

<?cs if:discussion.forum.id && !args.submit ?>
  <form id="edit-forum-form" class="addnew" method="post" action="<?cs var:discussion.href ?>/forum">
    <fieldset>
      <legend>
        Edit Forum:
      </legend>
      <div class="field">
        <label for="name">Name:</label><br/>
        <input type="text" id="name" name="name" value="<?cs var:discussion.name ?>"/><br/>
      </div>
      <div class="field">
        <label for="subject">Subject:</label><br/>
        <input type="text" id="subject" name="subject" value="<?cs var:discussion.subject ?>"/><br/>
      </div>
      <div class="field">
        <label for="description">Description:</label><br/>
        <input type="text" id="description" name="description" value="<?cs var:discussion.description ?>"/><br/>
      </div>
      <div class="field">
        <label for="moderators">Moderators:</label><br/>
        <?cs if:discussion.users.0 ?>
          <select id="moderators" name="moderators" multiple="on">
            <?cs each:user = discussion.users ?>
              <?cs set:selected = 0 ?>
              <?cs each:moderator = discussion.moderators ?>
                <?cs if:moderator == user ?>
                  <?cs set:selected = 1 ?>
                <?cs /if ?>
              <?cs /each ?>
              <?cs if:selected ?>
                <option value="<?cs var:user ?>" selected="selected"><?cs var:user ?></option>
              <?cs else ?>
                <option value="<?cs var:user ?>"><?cs var:user ?></option>
              <?cs /if ?>
            <?cs /each ?>
          </select><br/>
        <?cs else ?>
          <input type="text" id="moderators" name="moderators" value="<?cs var:discussion.moderators ?>"/><br/>
        <?cs /if ?>
      </div>
      <?cs if:discussion.groups.1.id ?>
        <div class="group">
          <label for="group">Forum Group:</label><br/>
          <select id="group" name="group">
            <?cs each:group = discussion.groups ?>
              <?cs if:group.id == discussion.group ?>
                <option value="<?cs var:group.id ?>" selected="selected"><?cs var:group.name ?></option>
              <?cs else ?>
                <option value="<?cs var:group.id ?>"><?cs var:group.name ?></option>
              <?cs /if ?>
            <?cs /each ?>
          </select><br/>
        </div>
      <?cs else ?>
        <input type="hidden" name="group" value=""/>
      <?cs /if ?>
      <div class="buttons">
        <input type="submit" name="submit" value="Edit"/>
        <input type="button" name="cancel" value="Cancel" onclick="location.href = '<?cs var:discussion.href ?>/forum'"/>
        <input type="hidden" name="forum" value="<?cs var:discussion.forum.id ?>"/>
        <input type="hidden" name="discussion_action" value="post-edit"/>
      </div>
    </fieldset>
  </form>
<?cs else?>
  <form id="new-forum-form" class="addnew" method="post" action="<?cs var:discussion.href ?>/forum">
    <fieldset>
      <legend>
        Add Forum:
      </legend>
      <div class="field">
        <label for="name">Name:</label><br/>
        <input type="text" id="name" name="name" value=""/><br/>
      </div>
      <div class="field">
        <label for="subject">Subject:</label><br/>
        <input type="text" id="subject" name="subject" value=""/><br/>
      </div>
      <div class="field">
        <label for="description">Description:</label><br/>
        <input type="text" id="description" name="description" value=""/><br/>
      </div>
      <div class="field">
        <label for="moderators">Moderators:</label><br/>
        <?cs if:discussion.users.0 ?>
          <select id="moderators" name="moderators" multiple="on">
            <?cs each:user = discussion.users ?>
              <option value="<?cs var:user ?>"><?cs var:user ?></option>
            <?cs /each ?>
          </select><br/>
        <?cs else ?>
          <input type="text" id="moderators" name="moderators" value=""/><br/>
        <?cs /if ?>
      </div>
      <?cs if:discussion.groups.1.id ?>
        <div class="group">
          <label for="group">Forum Group:</label><br/>
          <select id="group" name="group">
            <?cs each:group = discussion.groups ?>
              <option value="<?cs var:group.id ?>"><?cs var:group.name ?></option>
            <?cs /each ?>
          </select><br/>
        </div>
      <?cs else ?>
        <input type="hidden" name="group" value=""/>
      <?cs /if ?>
      <div class="buttons">
        <input type="submit" name="submit" value="Add"/>
        <input type="hidden" name="discussion_action" value="post-add"/>
      </div>
    </fieldset>
  </form>
<?cs /if ?>

<?cs if:discussion.forums.0.id ?>
<form method="post" action="<?cs var:discussion.href ?>/forum">
    <table id="forum-list" class="listing">
      <thead>
        <tr>
          <th class="sel">&nbsp;</th>
          <?cs call:my_sortable_th(discussion.order, discussion.desc, 'id', 'ID', discussion.href + '/forum' + '?') ?>
          <?cs call:my_sortable_th(discussion.order, discussion.desc, 'name', 'Name', discussion.href + '/forum' + '?') ?>
          <?cs call:my_sortable_th(discussion.order, discussion.desc, 'subject', 'Subject', discussion.href + '/forum' + '?') ?>
          <?cs call:my_sortable_th(discussion.order, discussion.desc, 'description', 'Description', discussion.href + '/forum' + '?') ?>
          <?cs call:my_sortable_th(discussion.order, discussion.desc, 'moderators', 'Moderators', discussion.href + '/forum' + '?') ?>
          <?cs if:discussion.groups.1.id ?>
            <?cs call:my_sortable_th(discussion.order, discussion.desc, 'forum_group', 'Group', discussion.href + '/forum' + '?') ?>
          <?cs /if ?>
        </tr>
      </thead>
      <tbody>
        <?cs each:forum = discussion.forums ?>
          <tr class="<?cs if:name(forum) % #2 ?>even<?cs else ?>odd<?cs /if ?>">
            <td class="sel">
              <input type="checkbox" name="selection" value="<?cs var:forum.id ?>"/>
            </td>
            <td class="id">
              <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                <div class="id"><?cs var:forum.id ?></div>
              </a>
            </td>
            <td class="name">
              <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                <div class="name"><?cs alt:forum.name ?>&nbsp;<?cs /alt ?></div>
              </a>
            </td>
            <td class="subject">
              <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                <div class="subject"><?cs alt:forum.subject ?>&nbsp;<?cs /alt ?></div>
              </a>
            </td>
            <td class="description">
              <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                <div class="description"><?cs alt:forum.description ?>&nbsp;<?cs /alt ?></div>
              </a>
            </td>
            <td class="moderators">
              <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                <div class="moderators"><?cs alt:forum.moderators ?>&nbsp;<?cs /alt ?></div>
              </a>
            </td>
            <?cs if:discussion.groups.1.id ?>
              <td class="group">
                <a href="<?cs var:discussion.href ?>/forum/<?cs var:forum.id ?>">
                  <?cs each:group = discussion.groups ?>
                    <?cs if:group.id == forum.group ?>
                      <div class="group"><?cs var:group.name ?></div>
                    <?cs /if ?>
                  <?cs /each ?>
                </a>
              </td>
            <?cs /if ?>
          </tr>
        <?cs /each ?>
      </tbody>
    </table>
    <div class="buttons">
      <input type="submit" name="remove" value="Remove selected items" />
      <input type="hidden" name="discussion_action" value="delete"/>
    </div>
  </form>
<?cs else ?>
  <p class="help">As long as you don't add any items to the list, this field
  will remain completely hidden from the user interface.</p>
  <br style="clear: right"/>
<?cs /if ?>
