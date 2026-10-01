import os
from werkzeug.utils import secure_filename
from middlewares.with_user import with_user
from middlewares.permission import permission
from models.settings import Setting
from utils.files import convert_to_webp
from flask import Blueprint, render_template, abort, redirect, request, flash,  url_for, current_app, session
from PIL import Image

settings_blueprint = Blueprint('admin_settings', __name__, template_folder='templates/admin')

@settings_blueprint.before_request
@with_user()
def check_admin_auth(user):
    """Verify that given routes only accessibles for admins"""
    if not "admin" in [r.role for r in user.roles]:
        return abort(403)
    
@settings_blueprint.route('/admin/settings/edit', methods=['GET'])
@permission('edit_settings')
def edit(user):
    from forms.admin.settings import SettingsForm
    form = SettingsForm()
    global_settings = Setting.query.filter_by(name='global').first()
    if global_settings:
        form.open.data = global_settings.meta.get('open', False)
        if global_settings.meta.get('contacts', None):
            form.contact_whatsapp.data = global_settings.meta.get('contacts').get('contact_whatsapp', '')
            form.contact_phone.data = global_settings.meta.get('contacts').get('contact_phone', '')
            form.contact_instagram.data = global_settings.meta.get('contacts').get('contact_instagram', '')
            form.contact_facebook.data = global_settings.meta.get('contacts').get('contact_facebook', '')
            form.contact_mail.data = global_settings.meta.get('contacts').get('contact_mail', '')

    social_settings = Setting.query.filter_by(name='social').first()
    if social_settings:
        form.tiktok_profile_url.data = social_settings.meta.get('tiktok_profile_url')
        form.youtube_profile_url.data = social_settings.meta.get('youtube_profile_url')
        form.instagram_profile_url.data = social_settings.meta.get('instagram_profile_url')
    header_settings = Setting.query.filter_by(name='header').first()
    if header_settings:
        form.site_name.data = header_settings.meta.get('site_name')
        form.site_description.data = header_settings.meta.get('site_description')
        form.support_mail.data = header_settings.meta.get('support_mail')
        form.processing_time.data = header_settings.meta.get('processing_time')
    privacy_policy_settings = Setting.query.filter_by(name='privacy_policy').first()
    if privacy_policy_settings:
        form.privacy_policy_en.data = privacy_policy_settings.meta.get('en', "")
        form.privacy_policy_it.data = privacy_policy_settings.meta.get('it', "")
    return render_template(
        '/admin/views/settings/edit.html', 
        user=user, 
        form=form, 
        global_settings=global_settings,
        header_settings=header_settings, 
        social_settings=social_settings, 
        privacy_policy_settings=privacy_policy_settings
    )

@settings_blueprint.route('/admin/settings/update', methods=['POST'])
@permission('edit_settings')
def update(user):
    from forms.admin.settings import SettingsForm
    form = SettingsForm()
    if form.validate_on_submit():
        relative_dir = "uploads/public"

        global_settings = Setting.query.filter_by(name='global').first()
        if not global_settings:
            global_settings = Setting(
                name='global',
                meta={}
            )
        global_settings.meta['open'] = form.open.data
        global_settings.meta['contacts'] = {}
        for key in [
            'contact_whatsapp',
            'contact_phone',
            'contact_instagram',
            'contact_facebook',
            'contact_mail'
        ]:
            global_settings.meta['contacts'][key] = ""
            form_var = getattr(form, key)
            if form_var.data:
                global_settings.meta['contacts'][key] = form_var.data

        homepage_it_file = form.homepage_it_image.data 
        if homepage_it_file and homepage_it_file.filename:
            ext = os.path.splitext(secure_filename(homepage_it_file.filename))[1].lower()
            if ext:
                relative_path = os.path.join(relative_dir, f"homepage_it{ext}").replace("\\", "/")
                absolute_path = os.path.join(current_app.root_path, "static/" + relative_path)
                homepage_it_file.save(absolute_path)
                convert_to_webp(absolute_path, quality=85)
                global_settings.meta['homepage_it_image'] = relative_path.split(".")[0] + ".webp"

        homepage_en_file = form.homepage_en_image.data
        if homepage_en_file and homepage_en_file.filename:
            ext = os.path.splitext(secure_filename(homepage_en_file.filename))[1].lower()
            if ext:
                relative_path = os.path.join(relative_dir, f"homepage_en{ext}").replace("\\", "/")
                absolute_path = os.path.join(current_app.root_path, "static/" +relative_path)
                homepage_en_file.save(absolute_path)
                convert_to_webp(absolute_path, quality=85)
                global_settings.meta['homepage_en_image'] = relative_path.split(".")[0] + ".webp"
        global_settings.save()

        privacy_policy_settings = Setting.query.filter_by(name='privacy_policy').first()
        if not privacy_policy_settings:
            privacy_policy_settings = Setting(
                name='privacy_policy',
                meta = {}
            )
        privacy_policy_settings.meta['en'] = form.privacy_policy_en.data
        privacy_policy_settings.meta['it'] = form.privacy_policy_it.data
        privacy_policy_settings.save()

        social_settings = Setting.query.filter_by(name='social').first()
        if not social_settings:
            social_settings = Setting(
                name='social',
                meta={}
            )
        social_settings.meta['tiktok_profile_url'] = form.tiktok_profile_url.data
        social_settings.meta['instagram_profile_url'] = form.instagram_profile_url.data
        social_settings.meta['youtube_profile_url'] = form.youtube_profile_url.data
        social_settings.save()

        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'public')
        os.makedirs(upload_dir, exist_ok=True)

        header_settings = Setting.query.filter_by(name='header').first()
        if not header_settings: 
            header_settings = Setting(
                name='header',
                meta={}
            )

        header_settings.meta['site_name'] = form.site_name.data
        header_settings.meta['site_description'] = form.site_description.data
        header_settings.meta['support_mail'] = form.support_mail.data
        header_settings.meta['processing_time'] = form.processing_time.data

        absolute_dir = os.path.join(current_app.root_path, relative_dir)
        os.makedirs(absolute_dir, exist_ok=True)

        header_file = form.header_image.data 
        if header_file and header_file.filename:
            ext = os.path.splitext(secure_filename(header_file.filename))[1].lower()
            if ext:
                relative_path = os.path.join(relative_dir, f"header{ext}").replace("\\", "/")
                absolute_path = os.path.join(current_app.root_path, "static/" + relative_path)
                header_file.save(absolute_path)
                convert_to_webp(absolute_path, quality=85)
                header_settings.meta['header'] = relative_path.split(".")[0] + ".webp"

        logo_file = form.logo_image.data
        if logo_file and logo_file.filename:
            ext = os.path.splitext(secure_filename(logo_file.filename))[1].lower()
            if ext:
                relative_path  = os.path.join(relative_dir, f"logo{ext}").replace("\\", "/")
                absolute_path = os.path.join(current_app.root_path, "static/" + relative_path)
                logo_file.save(absolute_path)
                convert_to_webp(absolute_path, quality=85)
                header_settings.meta['logo'] = relative_path.split(".")[0] + ".webp"
        header_settings.save()

        favicon_file = form.favicon_image.data
        if favicon_file and favicon_file.filename:
            favicon_stream = Image.open(favicon_file.stream)
            size = favicon_stream.size
            multi_size_ico_sizes = [
                (512, 512),
                (256, 256),
                (192, 192),
                (128, 128),
                (96, 96),
                (64, 64),
                (48, 48),
                (32, 32),
                (16, 16),
            ]

            if size not in multi_size_ico_sizes:
                flash("favicon.ico size must be one of these: 512x512, 256x256, 192x192, 128x128, 96x96, 64x64, 48x48, 32x32, 16x16", "danger")
                return redirect(url_for('admin_settings.edit'))
            
            idx = multi_size_ico_sizes.index(size)
            to_store_sizes = [f"-{x[0]}x{x[1]}.png" for x in multi_size_ico_sizes]

            relative_path = os.path.join(relative_dir, f"favicon.ico").replace("\\", "/")
            absolute_path = os.path.join(current_app.root_path, "static/" + relative_path)
            favicon_stream.save(absolute_path, format="ICO", sizes=multi_size_ico_sizes[idx:])
            header_settings.meta['favicon'] = relative_path

            for i, s in enumerate(to_store_sizes):
                relative_path = os.path.join(relative_dir, f"favicon{s}").replace("\\", "/")
                absolute_path = os.path.join(current_app.root_path, "static/" + relative_path)
                try: os.remove(absolute_path)
                except: pass
                if i < idx:
                    continue
                if i != 0:
                    favicon_stream = favicon_stream.resize(multi_size_ico_sizes[i])
                favicon_stream.save(absolute_path, format="PNG")

        header_settings.save()

        flash("Impostazioni aggiornate con successo", "success")
    else:
        if form.errors:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f"Error in {getattr(form, field).label.text}: {error}", "danger")
    return redirect(url_for('admin_settings.edit'))

@settings_blueprint.route('/admin/theme/<theme>')
def change_theme(theme):
    session['backoffice-theme'] = theme
    next_url = request.referrer or url_for('admin.admin')
    return redirect(next_url)