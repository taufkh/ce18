/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { BoardController } from "@board/board_controller";

patch(BoardController.prototype, {
    saveBoard() {
        if (!this.board.customViewId) {
            return;
        }
        return super.saveBoard(...arguments);
    },
});
