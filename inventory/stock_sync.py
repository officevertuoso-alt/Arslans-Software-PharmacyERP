
"""Record stock movements for full transaction sync."""
from __future__ import annotations

from inventory.models import StockMovement


def record_movement(*, product, delta: int, move_type: str, user=None,
                    batch=None, reference: str = '', notes: str = ''):
    if not delta:
        return None
    product.refresh_from_db(fields=['quantity'])
    return StockMovement.objects.create(
        product=product,
        batch=batch,
        move_type=move_type,
        quantity_delta=int(delta),
        quantity_after=int(product.quantity or 0),
        reference=(reference or '')[:64],
        notes=(notes or '')[:255],
        created_by=user if getattr(user, 'pk', None) else None,
    )
