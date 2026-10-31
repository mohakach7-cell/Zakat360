from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy import func

from . import admin_bp
from ...extensions import db
from ...models import Cause, Donation, AuditLog


def admin_required():
    if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
        flash('Accès admin requis.', 'danger')
        return False
    return True


def log_action(action: str, route: str, details: str = None):
    try:
        entry = AuditLog(user_id=(current_user.id if hasattr(current_user, 'id') else None), action=action, route=route, details=details)
        db.session.add(entry)
        db.session.commit()
    except Exception:
        db.session.rollback()


@admin_bp.route('/')
@login_required
def index():
    if not admin_required():
        return redirect(url_for('main.index'))
    stats = {
        'donations': db.session.query(func.count(Donation.id)).scalar() or 0,
        'causes': db.session.query(func.count(Cause.id)).scalar() or 0,
    }
    return render_template('admin/index.html', stats=stats)


@admin_bp.route('/causes', methods=['GET', 'POST'])
@login_required
def causes():
    if not admin_required():
        return redirect(url_for('main.index'))
    if request.method == 'POST':
        name = request.form.get('name')
        category = request.form.get('category')
        description = request.form.get('description')
        target = request.form.get('target_amount', '0')
        try:
            from decimal import Decimal
            cause = Cause(name=name, category=category, description=description, target_amount=Decimal(target), raised_amount=0, is_active=True)
            db.session.add(cause)
            db.session.commit()
            log_action('create_cause', '/admin/causes', f"name={name}")
            flash('Cause créée.', 'success')
        except Exception:
            db.session.rollback()
            flash('Erreur lors de la création de la cause.', 'danger')
        return redirect(url_for('admin.causes'))
    causes = Cause.query.order_by(Cause.created_at.desc()).all()
    return render_template('admin/causes.html', causes=causes)


@admin_bp.route('/causes/<int:cause_id>/toggle', methods=['POST'])
@login_required
def toggle_cause(cause_id):
    if not admin_required():
        return redirect(url_for('main.index'))
    cause = Cause.query.get_or_404(cause_id)
    cause.is_active = not cause.is_active
    db.session.commit()
    log_action('toggle_cause', f'/admin/causes/{cause_id}/toggle', f"is_active={cause.is_active}")
    flash('Statut de la cause mis à jour.', 'success')
    return redirect(url_for('admin.causes'))


@admin_bp.route('/donations/<int:donation_id>/status', methods=['POST'])
@login_required
def update_donation_status(donation_id):
    if not admin_required():
        return redirect(url_for('main.index'))
    donation = Donation.query.get_or_404(donation_id)
    status = request.form.get('status')
    if status not in {'pending', 'completed'}:
        flash('Statut invalide.', 'danger')
        return redirect(url_for('admin.index'))
    donation.status = status
    db.session.commit()
    log_action('update_donation_status', f'/admin/donations/{donation_id}/status', f"status={status}")
    flash('Statut du don mis à jour.', 'success')
    return redirect(url_for('admin.index'))