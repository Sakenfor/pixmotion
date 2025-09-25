# story_studio_project/plugins/assets/repository.py
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import func
from plugins.core.models import Asset


class AssetRepository:
    """
    Handles all direct database interactions for Asset objects.
    This class isolates SQLAlchemy logic from the AssetService.
    """

    def __init__(self, framework):
        self.db = framework.get_service("database_service")
        self.log = framework.get_service("log_manager")

    def get_by_path(self, path: str) -> Asset | None:
        session = self.db.get_session()
        try:
            return session.query(Asset).filter_by(path=path).one_or_none()
        finally:
            session.close()

    def get_by_id(self, asset_id: str) -> Asset | None:
        session = self.db.get_session()
        try:
            return session.query(Asset).filter_by(id=asset_id).one_or_none()
        finally:
            session.close()

    def get_path_by_id(self, asset_id: str) -> str | None:
        """Retrieves an asset's file path from its ID efficiently."""
        session = self.db.get_session()
        try:
            return session.query(Asset.path).filter_by(id=asset_id).scalar()
        finally:
            session.close()

    def add(self, asset: Asset) -> Asset:
        session = self.db.get_session()
        try:
            session.add(asset)
            session.commit()
            self.log.info(f"Added new asset to DB: {asset.path}")
            return asset
        except Exception as e:
            session.rollback()
            self.log.error(f"Error adding asset to DB {asset.path}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_existing_paths_in_folder(self, folder_path: str) -> set:
        """Gets all paths already in the DB for a given folder in one query."""
        session = self.db.get_session()
        try:
            return {
                p[0]
                for p in session.query(Asset.path).filter(
                    Asset.path.startswith(folder_path)
                )
            }
        finally:
            session.close()

    def update_rating(self, asset_id: str, rating: int) -> bool:
        session = self.db.get_session()
        try:
            asset = session.query(Asset).filter_by(id=asset_id).one()
            asset.rating = rating
            session.commit()
            self.log.info(f"Updated rating for asset {asset_id} to {rating}")
            return True
        except NoResultFound:
            self.log.warning(f"Could not find asset {asset_id} to update rating.")
            return False
        finally:
            session.close()

    def find_duplicates(self) -> list[Asset]:
        """Finds assets with identical file hashes."""
        session = self.db.get_session()
        try:
            duplicate_hashes_sq = (
                session.query(Asset.id)
                .group_by(Asset.id)
                .having(func.count(Asset.id) > 1)
                .scalar_subquery()
            )
            duplicates = (
                session.query(Asset)
                .filter(Asset.id.in_(duplicate_hashes_sq))
                .order_by(Asset.id, Asset.path)
                .all()
            )
            return duplicates
        finally:
            session.close()

    def delete_by_path(self, path: str) -> Asset | None:
        """Deletes an asset from the database by its path and returns the deleted object."""
        session = self.db.get_session()
        try:
            asset = session.query(Asset).filter_by(path=path).one_or_none()
            if asset:
                session.delete(asset)
                session.commit()
                return asset
            return None
        except Exception as e:
            session.rollback()
            self.log.error(f"Error deleting asset from DB {path}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_assets_in_clipboard(self, clipboard_dir: str) -> list[Asset]:
        session = self.db.get_session()
        try:
            return (
                session.query(Asset).filter(Asset.path.startswith(clipboard_dir)).all()
            )
        finally:
            session.close()

    def delete_many(self, assets: list[Asset]):
        session = self.db.get_session()
        try:
            for asset in assets:
                # Re-attach the object to the current session before deleting
                session.delete(session.merge(asset))
            session.commit()
        except Exception as e:
            session.rollback()
            self.log.error(f"Error during bulk delete: {e}", exc_info=True)
        finally:
            session.close()
