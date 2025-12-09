program SmartHome {
	string inputPass = "" //Se mantiene en blanco porque será operado en el prototipo

   lock front_door() {
      state:
          boolean is_locked = false
          $PASS = "1235"
   }
   // Rutina consolidada que maneja todas las acciones programadas.
   routine daily_schedule {

		action check_pass {
	    	 when: (front_door.$PASS == inputPass) -> 
			   front_door.force_unlock,
				front_door.is_locked = false
		}
   }
}



