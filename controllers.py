"""
This file defines actions, i.e. functions the URLs are mapped into
The @action(path) decorator exposed the function at URL:

    http://127.0.0.1:8000/{app_name}/{path}

If app_name == '_default' then simply

    http://127.0.0.1:8000/{path}

If path == 'index' it can be omitted:

    http://127.0.0.1:8000/

The path follows the bottlepy syntax.

@action.uses('generic.html')  indicates that the action uses the generic.html template
@action.uses(session)         indicates that the action uses the session
@action.uses(db)              indicates that the action uses the db
@action.uses(T)               indicates that the action uses the i18n & pluralization
@action.uses(auth.user)       indicates that the action requires a logged in user
@action.uses(auth)            indicates that the action requires the auth object

session, db, T, auth, and tempates are examples of Fixtures.
Warning: Fixtures MUST be declared with @action.uses({fixtures}) else your app will result in undefined behavior
"""

import uuid

from py4web import action, request, abort, redirect, URL, Field
from py4web.utils.form import Form, FormStyleBulma
from py4web.utils.url_signer import URLSigner

from yatl.helpers import A
from . common import db, session, T, cache, auth, signed_url


url_signer = URLSigner(session)

# The auth.user below forces login.
@action('index')
@action.uses('index.html', auth.user, db, session)
def index():
    user = auth.current_user.get('email')
    rows = db(db.person.user_email == user).select()
    for i, row in enumerate(rows):
        contact_id = row["id"]
        numbers = db(db.contact.contact_id == contact_id).select().as_list()
        format_phones = ""
        for i2, num in enumerate(numbers):
            format_phones += num["phone"]
            format_phones += " (" + num["kind"]+ ")"
            if(i2+1 != len(numbers)):
                format_phones += ", "
        rows[i]["phone_numbers"] = format_phones
    return dict(rows=rows, url_signer=url_signer)
    
@action('phone_index/<contact_id>', method=['GET'])
@action.uses('phone_index.html', auth.user, db, session)
def phone_index(contact_id=None):
    curr_user = auth.current_user.get('email')
    p = db.person[contact_id]
    first_name = db.person[contact_id].first_name
    last_name = db.person[contact_id].last_name
    if p is None:
        redirect(URL('index'))
    elif p.user_email != curr_user:
        redirect(URL('index'))
    else:
        rows = db(db.contact.contact_id == contact_id).select()
    return dict(rows=rows, contact_id=contact_id, name=first_name + " " + last_name, url_signer=url_signer)
    
@action('add_contact', method=['GET', 'POST'])
@action.uses('contact_form.html', auth.user, db, session)
def add_contact():
    form = Form(db.person, csrf_session=session, formstyle=FormStyleBulma)
    if form.accepted:
        # We always want POST requests to be redirected as GETs.
        redirect(URL('index'))
    return dict(form=form)
    
@action('add_phone/<contact_id>', method=['GET', 'POST'])
@action.uses('phone_form.html', auth.user, db, session)
def add_phone(contact_id=None):
    curr_user = auth.current_user.get('email')
    first_name = db.person[contact_id].first_name
    last_name = db.person[contact_id].last_name
    p = db.person[contact_id]
    if p is None:
        redirect(URL('index'))
    elif p.user_email != curr_user:
        redirect(URL('index'))
    else:
        form = Form([Field('phone'), Field('kind')], csrf_session=session, formstyle=FormStyleBulma)
        if form.accepted:
            db.contact.insert(phone=form.vars["phone"], kind=form.vars["kind"], contact_id=contact_id)
            # We always want POST requests to be redirected as GETs.
            redirect(URL('phone_index', contact_id))    
    return dict(form=form, contact_id=contact_id, name=first_name + " " + last_name)

@action('edit_contact/<contact_id>', method=['GET', 'POST'])
@action.uses('contact_form.html', auth.user, db, session, signed_url)
def edit_contact(contact_id=None):
    curr_email = auth.current_user.get('email')
    p = db.person[contact_id]
    if p is None:
        # Nothing to edit.  This should happen only if you tamper manually with the URL.
        redirect(URL('index'))
    elif db.person[contact_id].user_email != curr_email:
        redirect(URL('index'))
    form = Form(db.person, record=p, deletable=False, csrf_session=session, formstyle=FormStyleBulma)
    if form.accepted:
        # We always want POST requests to be redirected as GETs.
        redirect(URL('index'))
    return dict(form=form)
    
@action('edit_phone/<contact_id>/<row_id>', method=['GET', 'POST'])
@action.uses('phone_form.html', auth.user, db, session)
def edit_phone(contact_id=None, row_id=None):
    curr_user = auth.current_user.get('email')
    first_name = db.person[contact_id].first_name
    last_name = db.person[contact_id].last_name
    p = db.person[contact_id]
    num = db.contact[row_id]
    if p is None:
        redirect(URL('index'))
    elif p.user_email != curr_user:
        redirect(URL('index'))
    else:
        form = Form([Field('phone'), Field('kind')], record=num, deletable=False, csrf_session=session, formstyle=FormStyleBulma)
    if form.accepted:
        db(db.contact.id == row_id).update(phone=form.vars["phone"], kind=form.vars["kind"])
        # We always want POST requests to be redirected as GETs.
        redirect(URL('phone_index', contact_id))
    return dict(form=form, user=auth.user, name=first_name + " " + last_name)
    
@action('delete_contact/<contact_id>', method=['GET', 'POST'])
@action.uses(auth.user, db, session, url_signer.verify())
def delete_person(contact_id=None):
    # We delete the contact.
    p = db.person[contact_id]
    if p is None:
        # Nothing to edit.  This should happen only if you tamper manually with the URL.
        redirect(URL('index'))
    db(db.person.id == contact_id).delete()
    deleted = db.person[contact_id]
    if deleted is None:
        # We always want POST requests to be redirected as GETs.
        redirect(URL('index'))
    return dict(deleted=deleted)
    
@action('delete_phone/<contact_id>/<row_id>', method=['GET', 'POST'])
@action.uses(auth.user, db, session, url_signer.verify())
def delete_phone(contact_id=None, row_id=None):
    curr_user = auth.current_user.get('email')
    p = db.person[contact_id]

    if p is None:
        redirect(URL('index'))
    elif row_id is None:
        redirect(URL('index'))
    else:
        if(p.user_email == curr_user):
            db(db.contact.id == row_id).delete()
        redirect(URL('phone_index', contact_id))
