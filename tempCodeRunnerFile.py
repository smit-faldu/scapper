        except Exception as e:
            logger.error(f"Error extracting investor data: {str(e)}")
        
        logger.info(f"Extracted {len(investors)} investors from the page")
        return investors